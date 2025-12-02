```py
# Strategy rationale (embedded as comments for clarity):
# - Goal: Kill the Dragon as fast as possible while avoiding catastrophic loss of attackers.
# - Core rules we follow:
#   - All Warriors must go to the Cave to attack the Dragon.
#   - Farmers stay in the Village to farm and to spawn new villagers.
# - Spawning policy (improved, cautious but proactive):
#   - We cap spawns per step to avoid explosive farmer growth that can bloat the village
#     and delay dragon攻 attack progression.
#   - We spawn at most 1 Farmer-spawn (2 Farmers, cost 10 Wheat) per step in early stages,
#     and up to 2 Farmer-spawns (still in a safe bound) in later steps if Wheat allows.
#   - After farmers are allocated to farmer-spawns, we spawn Warrior-spawns (2 Warriors, cost 12 Wheat)
#     as available and only up to a small cap per step (1 or 2 depending on step) to boost DPS.
# - Rationale for step-based caps:
#   - Early steps prioritize accelerating population growth to increase long-term DPS.
#   - Later steps prioritize turning existing wheat into additional Warriors to finish the Dragon sooner.
# - Cave behavior:
#   - Warriors attack every turn; Farmers stay in the Village (they will move to cave in next steps
#     after spawning if needed). This aligns with the explicit constraint and reduces immediate risk to all attackers.
#
# Implementation note:
# - The environment.assign_group(component, group_id) method is used for all assignments.
# - The step argument is used to adapt spawn rates over time.
#
# This adaptation aims to produce a more balanced growth of attackers while maintaining a steady
# stream of wheat to fund spawning, with a bias towards earlier Warrior generation when Wheat is abundant.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Always send Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available at the Farm
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine farmer-spawns this step (cap at 1 in early steps, up to 2 later)
        farm_spawns = 0
        if len(farmers) >= 2 and wheat >= 10:
            if step < 5:
                farm_spawns = min(1, len(farmers) // 2, wheat // 10)
            else:
                farm_spawns = min(2, len(farmers) // 2, wheat // 10)

        wheat_after_farm = wheat - farm_spawns * 10
        remaining_farmers = len(farmers) - 2 * farm_spawns

        # Determine warrior-spawns this step (cap at 1 in early steps, up to 2 later)
        war_spawns = 0
        if remaining_farmers >= 2 and wheat_after_farm >= 12:
            if step < 3:
                war_spawns = min(1, remaining_farmers // 2, wheat_after_farm // 12)
            else:
                war_spawns = min(2, remaining_farmers // 2, wheat_after_farm // 12)

        spawn_farmer_count = 2 * farm_spawns
        spawn_warrior_count = 2 * war_spawns

        # Assign farmers to appropriate groups
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, attack with Warriors; Farmers should stay in Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```