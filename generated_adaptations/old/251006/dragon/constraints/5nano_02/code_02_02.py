# Reasoning and adaptation strategy:
# Objective: Reduce the exposure of fields (wheat) to losses while still pursuing a fast kill of the Dragon.
# Observations:
# - Warriors must go to the Cave to attack; Farmers stay in the Village.
# - Spawning uses two villagers plus Wheat (12 for Warriors, 10 for Farmers) to create new villagers.
# - The Dragon retaliates in the Cave, potentially killing villagers there (40% chance 1 damage to all in cave, 20% chance to eat one random cave villager).
# - To minimize wheat losses, we should avoid over-committing villagers to the Cave at once and avoid aggressive spawning that drains Wheat too quickly if it risks waste (e.g., not enough turns left to utilize new villagers).
# Strategy refinements:
# - Keep all Warriors in the Cave (as required) to maximize DPS, but avoid flooding the Cave with too many villagers at once by moderating spawns per step.
# - In the Village:
#   - Allow at most 1 Warrior spawn per step (needs 2 Farmers and 12 Wheat) to grow DPS gradually and limit wheat consumption.
#   - Allow at most 1 Farmer spawn per step (needs 2 Farmers and 10 Wheat) if Wheat remains after Warrior spawns.
#   - Prioritize keeping a healthy farming population to sustain Wheat production for future spawns.
# - This approach trades a bit of per-step speed for reduced Wheat consumption spikes and potentially fewer total casualties, while still providing a path to timely Dragon kill within 30 steps in typical runs.
# - Implementation note: We implement a conservative, per-step spawning cap (0 or 1 for each spawn type) and assign all Warriors to the cave's attack group. Farmers not spawning go to farming to keep Wheat production stable.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role (read-only attributes)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the Farm (fall back to 0 if not available)
        available_wheat = 0
        try:
            available_wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            available_wheat = 0

        # Number of farmers currently available
        num_farmers = len(farmers)

        # Conservative per-step spawns:
        # - Warrior spawn: at most 1 per step (needs 2 farmers and 12 wheat)
        max_war_spawns = min(1, num_farmers // 2, available_wheat // 12)

        # Update wheat and farmers after potential Warrior spawn
        remaining_wheat_after_war = available_wheat - max_war_spawns * 12
        remaining_farmers_after_war = num_farmers - max_war_spawns * 2

        # - Farmer spawn: at most 1 per step (needs 2 farmers and 10 wheat)
        max_farm_spawns = min(1, remaining_farmers_after_war // 2, remaining_wheat_after_war // 10)

        # Assign groups
        # 1) Warriors go to Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn Warrior: two farmers per spawn
        spawn_warrior_vills = farmers[0 : 2 * max_war_spawns]
        for f in spawn_warrior_vills:
            environment.assign_group(f, "spawn warrior")

        # 3) Spawn Farmer: two farmers per spawn
        start_for_farm_spawns = 2 * max_war_spawns
        spawn_farmer_vills = farmers[start_for_farm_spawns : start_for_farm_spawns + 2 * max_farm_spawns]
        for f in spawn_farmer_vills:
            environment.assign_group(f, "spawn farmer")

        # 4) Remaining farmers go to farming in the Village
        remaining_farmers = farmers[start_for_farm_spawns + 2 * max_farm_spawns :]
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack the Dragon.
        # Farmers should stay in the Village (not sent to cave this turn).
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")