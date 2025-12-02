```py
# Strategy rationale (embedded as comments for clarity):
# - Goal: Kill the Dragon as fast as possible while balancing risk from Dragon attacks.
# - Core rules we follow:
#   - All Warriors must go to the Cave to attack the Dragon.
#   - Farmers stay in the Village to farm and to spawn new villagers.
# - Enhanced spawning policy (adaptive and risk-aware):
#   - We keep a dynamic focus on Warrior spawning when the Dragon is strong (high HP),
#     and we shift toward Farmer farming when the Dragon is weaker to sustain long-term DPS.
#   - We cap per-step spawns to avoid explosive growth that can expose too many villagers to
#     Dragon attacks in the Cave.
# - Assignment behavior:
#   - Warriors are sent to the Cave (attack) at once.
#   - Farmers are assigned to one of three spawn groups or to farming, based on
#     available Wheat and current Dragon HP.
# - Cave behavior:
#   - All Warriors attack; Farmers stay in the Village (safer from Dragon attacks in Cave).
# - This strategy aims for a faster kill by boosting early DPS with Warrior spawns when the Dragon HP is high,
#   while ensuring Wheat is invested for sustained growth.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Always send Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available at the Farm
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        farm_spawns = 0
        war_spawns = 0

        # Determine possible spawns given resources
        if wheat >= 10 and len(farmers) >= 2:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

            if dragon_hp > 25:
                # Aggressively spawn Warriors first when the dragon is strong
                # Use as many Farmer-spawns as possible, then spawn Warriors if possible
                # We choose to spawn all possible farmer-spawns (up to 2 per step cap via next lines)
                farm_spawns = max_farm_spawns
                wheat_after_farm = wheat - farm_spawns * 10
                rem_farmers = len(farmers) - 2 * farm_spawns

                if rem_farmers >= 2 and wheat_after_farm >= 12:
                    max_war_spawns = min(rem_farmers // 2, wheat_after_farm // 12)
                    war_spawns = min(max_war_spawns, 2)
            else:
                # In calmer steps, spawn at most 1 Farmer-spawn to steadily grow wheat
                farm_spawns = min(1, max_farm_spawns)
                wheat_after_farm = wheat - farm_spawns * 10
                rem_farmers = len(farmers) - 2 * farm_spawns

                if rem_farmers >= 2 and wheat_after_farm >= 12:
                    max_war_spawns = min(rem_farmers // 2, wheat_after_farm // 12)
                    war_spawns = min(max_war_spawns, 2)

        spawn_farmer_count = 2 * farm_spawns
        spawn_warrior_count = 2 * war_spawns

        # Assign farmers to the correct spawn groups or farming
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, attack with Warriors; Farmers stay in Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```