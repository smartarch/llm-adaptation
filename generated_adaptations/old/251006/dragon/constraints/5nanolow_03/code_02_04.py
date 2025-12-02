from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components: List, environment, group_ids, step: int):
        """
        In the village:
        - All Warriors go to the cave (attack).
        - For Farmers, use farm wheat to spawn new villagers:
          - For every 2 farmers assigned to "spawn farmer" and 10 wheat, spawn a Farmer.
          - For every 2 farmers assigned to "spawn warrior" and 12 wheat, spawn a Warrior.
        - Any remaining farmers are assigned to the farm.
        This implementation uses a deterministic, non-overlapping assignment
        to ensure every component is assigned exactly once per call.
        """
        # Split by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning logic among farmers using farm wheat
        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Spawn farmers greedily: use 2 farmers per spawn, 10 wheat per spawn
        spawns_farm = min(len(farmers) // 2, farm_wheat // 10)

        idx = 0
        used_wheat = 0

        # Assign first 2*spawns_farm farmers to "spawn farmer"
        for _ in range(spawns_farm):
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            idx += 2
            used_wheat += 10

        # Wheat left after spawning farmers
        wheat_left = max(0, farm_wheat - used_wheat)

        # Spawn warriors if possible: need two farmers and 12 wheat
        spawns_warrior = min((len(farmers) - idx) // 2, wheat_left // 12)

        # Assign next 2*spawns_warrior farmers to "spawn warrior"
        for _ in range(spawns_warrior):
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            idx += 2
            wheat_left -= 12

        # Remaining farmers go to farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: All components should now be assigned exactly once in this step.

    def assign_in_cave(self, components: List, environment, group_ids, step: int):
        """
        In the cave:
        - Warriors go to the attack group
        - Farmers go to the village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")