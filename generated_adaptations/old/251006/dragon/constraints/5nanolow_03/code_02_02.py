from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components: List, environment, group_ids, step: int):
        """
        In the village:
        - Warriors go to cave (attack).
        - Farmers try to spawn new villagers if wheat is available, otherwise stay on the farm.
        Spawning:
          - For every 2 farmers assigned to "spawn farmer" and 10 wheat, spawn a Farmer.
          - For every 2 farmers assigned to "spawn warrior" and 12 wheat, spawn a Warrior.
        Ensure every component is assigned exactly once.
        """
        assigned = set()

        # Split by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to cave (attack)
        for w in warriors:
            if w not in assigned:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 2) Spawning logic among farmers using farm wheat
        farm_wheat = getattr(environment.farm, "wheat", 0)

        idx = 0
        used_wheat = 0
        spawned = set()

        # Spawn farmers first: need 2 farmers and 10 wheat per spawn
        while idx + 1 < len(farmers) and used_wheat + 10 <= farm_wheat:
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            if f1 not in assigned:
                environment.assign_group(f1, "spawn farmer")
                assigned.add(f1)
            if f2 not in assigned:
                environment.assign_group(f2, "spawn farmer")
                assigned.add(f2)
            spawned.update([f1, f2])
            used_wheat += 10
            idx += 2

        # Wheat left after spawning farmers
        wheat_left = max(0, farm_wheat - used_wheat)

        # Spawn warriors if possible: need two farmers and 12 wheat
        while idx + 1 < len(farmers) and wheat_left >= 12:
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            if f1 not in assigned:
                environment.assign_group(f1, "spawn warrior")
                assigned.add(f1)
            if f2 not in assigned:
                environment.assign_group(f2, "spawn warrior")
                assigned.add(f2)
            spawned.update([f1, f2])
            idx += 2
            wheat_left -= 12

        # Remaining farmers go to farm
        for i in range(idx, len(farmers)):
            f = farmers[i]
            if f not in assigned:
                environment.assign_group(f, "farm")
                assigned.add(f)

        # Defensive: any stray component not yet assigned gets default to farm
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(c)

    def assign_in_cave(self, components: List, environment, group_ids, step: int):
        """
        In the cave:
        - Warriors attack the Dragon (group "attack")
        - Other villagers stay in the village (group "village")
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")

        # Any unassigned should be placed to village by safety (unlikely, but keep robust)
        for c in components:
            # If somehow not assigned yet, put to village
            if not self._is_assigned(c, environment):
                environment.assign_group(c, "village")

    # Helpers (lightweight, relying on environment state)
    def _is_assigned(self, component, environment) -> bool:
        # If the environment API had a query, we'd use it. As a fallback, assume assigned.
        # Here we implement a best-effort: try to detect by using a known attribute.
        # Since we can't query, return False to allow fallback assignment in test-safe way.
        return False