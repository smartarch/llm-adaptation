```py
# Strategy reasoning (embedded as comments for clarity)
# Objective: Kill the Dragon as fast as possible. We must balance DPS from Warriors with wheat production from Farmers,
# while keeping villagers alive long enough to keep spawning more helpers.
#
# Key observations:
# - Warriors in the Cave contribute 3 damage per attack; Farmers contribute 1 damage when attacking, but mainly
#   serve as wheat producers in the Village (5 wheat per farming action for Farmers, 2 for Warriors).
# - Dragon retaliation is risky: ~40% chance to deal 1 damage to every villager in the Cave and ~20% chance to eat one
#   random villager in the Cave. We should minimize the number of villagers in the Cave to reduce losses, but still aim
#   for enough DPS to kill the Dragon within 30 steps.
# - Spawning logic: For every two villagers assigned to a spawn group and enough wheat, one new villager is spawned.
#   Spawning Farmers uses 10 wheat; spawning Warriors uses 12 wheat.
#
# Improved strategy:
# - Always keep all Warriors in the Cave to maximize early DPS. Farmers stay in the Village to farm and accumulate wheat.
# - Spawn strategies should be conservative but opportunistic:
#   - If we have at least 2 Farmers and wheat >= 10, spawn a new Farmer (2 Farmers move to "spawn farmer" group).
#   - After spawning Farmers, if we have at least 2 additional Farmers and enough wheat for a Warrior (wheat >= 12),
#     spawn a new Warrior (2 Farmers move to "spawn warrior" group).
# - This yields a gradual but steady increase in total villagers and DPS while attempting to avoid starving wheat production.
# - All components are explicitly reassigned to a group every step to satisfy the "explicit reassignment" requirement.
#
# This version slightly tightens the spawning logic by computing farmer spawns and warrior spawns from the same wheat pool
# and ensuring we don't overspend wheat in a single step.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants (must match exactly)
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave; Farmers stay in village farming by default
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat from the farm
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Spawn farmers if possible (two farmers with 10 wheat)
        num_farmers = len(farmers)
        spawn_farmers_pairs = min(num_farmers // 2, wheat // 10)
        spawn_farmers_count = 2 * spawn_farmers_pairs

        if spawn_farmers_pairs > 0:
            # Move the first 2*spawn_farmers_pairs farmers to the spawn farmer group
            for c in farmers[:spawn_farmers_count]:
                environment.assign_group(c, SPAWN_FARMER)

        # Recompute wheat after spending on farmer spawns
        wheat_after_farmers = wheat - (spawn_farmers_pairs * 10)

        # Step 3: Spawn warriors if possible from remaining farmers
        remaining_farmers = farmers[spawn_farmers_count:]
        warrior_spawns = min(len(remaining_farmers) // 2, wheat_after_farmers // 12)
        spawn_warriors_count = 2 * warrior_spawns

        if spawn_warriors_count > 0:
            for c in remaining_farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # The rest of the farmers that are not in spawn groups stay farming
        rest_start = spawn_farmers_count + spawn_warriors_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Note:
        # - Warriors are already directed to the "cave" group by default.
        # - Spawn groups will cause new villagers to appear in subsequent steps per game rules.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in the cave should go back to the village
                environment.assign_group(c, VILLAGE)

        # If there happens to be any Farmer in the Cave due to edge cases, they are moved to the village.
```