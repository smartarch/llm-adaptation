```py
# Strategy rationale (embedded as comments for clarity)
# Objective
# - Kill the Dragon as fast as possible within 30 steps.
# - Maintain wheat production to enable spawning new villagers over time.
# - Respect the policy: All Warriors must go to the Cave and attack; Farmers stay in the Village to farm and spawn.
#
# Observations guiding this iteration
# - Spawning is expensive: 10 wheat for a Farmer, 12 wheat for a Warrior, and requires two villagers assigned to the spawn group.
# - To keep wheat growing, we should avoid starving the Village of Farmers. Spawning too aggressively can deplete wheat too fast.
# - A measured, turn-by-turn spawning policy tends to perform better:
#   - Do at most one Warrior pair per turn (2 Warriors total) to boost DPS without overly reducing farming capacity.
#   - After allocating Warrior spawns, use any remaining Farmers and Wheat to spawn Farmers (but cap to a small number per turn to avoid wheat starvation).
# - This approach keeps a steady DPS increase while preserving wheat production for ongoing spawning.
# - Explicit reassignment remains in place to satisfy the requirement.

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
        # Warriors are kept in cave by default; classification is only for logic
        # (not strictly needed for behavior, but helps readability)
        # warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors -> cave; Farmers -> farm
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat (guard against missing farm)
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        num_farmers = len(farmers)

        # Step 2: Optional Warrior spawns (at most 1 pair per turn to be conservative)
        spawn_warriors_count = 0
        if num_farmers >= 4 and wheat >= 12:
            # Maximum warrior spawns allowed by resources, but cap to 1 pair per turn
            max_by_resources = min((num_farmers - 2) // 2, wheat // 12)
            max_warrior_spawns = min(max_by_resources, 1)  # cap to 1 pair (2 warriors)
            spawn_warriors_count = 2 * max_warrior_spawns

        if spawn_warriors_count > 0:
            # Move the first spawn_warriors_count farmers to the SPAWN_WARRIOR group
            for c in farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # Step 3: Farmer spawns after Warrior spawns
        remaining_farmers_after_war = num_farmers - spawn_warriors_count
        remaining_wheat_after_war = wheat - (spawn_warriors_count * 12)

        spawn_farmers_count = 0
        if remaining_farmers_after_war >= 2 and remaining_wheat_after_war >= 10:
            max_farmer_spawns = min(remaining_farmers_after_war // 2,
                                    remaining_wheat_after_war // 10)
            # Cap to a small number to avoid exhausting wheat too quickly
            max_farmer_spawns = min(max_farmer_spawns, 2)  # at most 2 pairs (4 farmers) per turn
            spawn_farmers_count = 2 * max_farmer_spawns

            if spawn_farmers_count > 0:
                for c in farmers[spawn_warriors_count:
                                 spawn_warriors_count + spawn_farmers_count]:
                    environment.assign_group(c, SPAWN_FARMER)

        # Step 4: The rest stay farming
        rest_start = spawn_warriors_count + spawn_farmers_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Notes:
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