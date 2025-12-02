```py
# Strategy reasoning (embedded as comments for clarity)
# Objective: Kill the Dragon as fast as possible while maintaining wheat production to spawn new villagers.
# Observations:
# - Warriors (DPS=3) are most effective in the Cave, but lose more health due to dragon retaliation if kept there long.
# - Farmers (HP=4) produce wheat (5 wheat when farming) and should remain in the Village to sustain spawning.
# - Spawn mechanic: For every two villagers in a spawn group and enough wheat, a new villager is spawned.
#   - Spawn Farmer costs 10 wheat; Spawn Warrior costs 12 wheat.
# - We want to scale up DPS early but never starve wheat production. A conservative but scalable spawning policy is:
#   - Keep all Warriors in the Cave (policy requirement).
#   - In the Village, spawn Warriors only if we can guarantee that at least 3 Farmers remain to continue farming (to sustain wheat).
#   - Spawn Farmers with any remaining wheat after warrior spawns, ensuring at least two Farmers are available for each spawn.
#   - Always reassign all villagers to a group every step to satisfy the explicit reassignment rule.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants (must match exact strings)
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        # Warriors are kept in cave by default; classify for convenience
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave; Farmers stay in village farming by default
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Conservative Warrior spawns
        # Spawn Warriors only if we can spare at least 3 Farmers to remain farming afterwards and we have enough wheat
        num_farmers = len(farmers)
        spawn_warriors_count = 0
        if num_farmers >= 4 and wheat >= 12:
            # Max possible warrior spawns given resources, but ensure at least 3 farmers remain
            max_possible_by_resources = min(num_farmers // 2, wheat // 12)
            # Reserve at least 3 farmers for farming after spawning warriors
            if num_farmers - 2 * max_possible_by_resources >= 3:
                spawn_warriors_count = 2 * max_possible_by_resources
            else:
                # Compute the largest number of warrior spawns we can do while keeping 3 farmers
                max_by_reserve = max(0, (num_farmers - 3) // 2)
                spawn_warriors_count = 2 * min(max_possible_by_resources, max_by_reserve)

        if spawn_warriors_count > 0:
            for c in farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # Step 3: After warrior spawns, compute farmer spawns
        remaining_farmers = num_farmers - spawn_warriors_count
        remaining_wheat = wheat - (spawn_warriors_count * 12)

        spawn_farmers_count = 0
        if remaining_farmers >= 2 and remaining_wheat >= 10:
            max_farmer_spawns = min(remaining_farmers // 2, remaining_wheat // 10)
            spawn_farmers_count = 2 * max_farmer_spawns
            if spawn_farmers_count > 0:
                for c in farmers[spawn_warriors_count:
                                 spawn_warriors_count + spawn_farmers_count]:
                    environment.assign_group(c, SPAWN_FARMER)

        # Step 4: The rest stay farming
        rest_start = spawn_warriors_count + spawn_farmers_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Note:
        # - Warriors are already directed to the "cave" group by default.
        # - Spawn groups will create new villagers in subsequent steps per game rules.

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
                # Farmers in the cave go back to the village
                environment.assign_group(c, VILLAGE)

        # Note: If there are any Farmers in the Cave due to edge cases, they are moved to village.
```