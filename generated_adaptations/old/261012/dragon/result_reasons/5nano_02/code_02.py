import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors in Village to Cave (to ensure attack capability)
        # - Farm the Farmers in Village
        # - Spawn a small number of new Farmers and Warriors if wheat/resources allow
        # - Use remaining Farmers to farm

        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, remaining villagers in Village are only Farmers (if any)
        # 2) Spawning decision based on available wheat and number of farmers
        available_wheat = environment.farm.wheat

        F_spawns = 0
        W_spawns = 0

        # Simple deterministic heuristic:
        # - If we can, spawn 2 Farmers (needs 4 farmers and 20 wheat)
        if len(farmers) >= 4 and available_wheat >= 20:
            F_spawns = 2
            available_wheat -= 20
        else:
            # else, try to spawn 1 Farmer if possible (needs 2 farmers and 10 wheat)
            if len(farmers) >= 2 and available_wheat >= 10:
                F_spawns = 1
                available_wheat -= 10

        # After farmer spawns, try to spawn 1 Warrior if we have enough remaining farmers and wheat
        remaining_farmers_for_warrior = len(farmers) - (2 * F_spawns)
        if remaining_farmers_for_warrior >= 2 and available_wheat >= 12:
            W_spawns = 1
            available_wheat -= 12

        # Ensure we do not exceed available farmers when assigning spawn groups
        total_needed_spawn_villagers = 2 * (F_spawns + W_spawns)
        if total_needed_spawn_villagers > len(farmers):
            # Reduce spawns proportionally, preferring Farmer spawns
            max_pairs = len(farmers) // 2
            F_spawns = min(F_spawns, max_pairs)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))
            total_needed_spawn_villagers = 2 * (F_spawns + W_spawns)

        # 3) Assign spawns from farmers
        idx = 0
        # Spawn Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
        # Spawn Warriors
        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # Note: Any Warriors already moved to Cave at the start remain in the Cave
        # and will be handled in assign_in_cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy in Cave:
        # - All Warriors in Cave should attack Dragon
        # - All Farmers in Cave should go back to Village (stay in Village)

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any non-Warrior) should return to Village
                environment.assign_group(c, "village")