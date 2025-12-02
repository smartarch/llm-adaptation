from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components: List, environment, group_ids, step: int):
        """
        In the village:
        - All Warriors go to the cave (attack).
        - Farmers can spawn new villagers if there is enough wheat:
          - For every 2 farmers assigned to "spawn farmer" and 10 wheat, spawn a Farmer.
          - For every 2 farmers assigned to "spawn warrior" and 12 wheat, spawn a Warrior.
        - Any remaining farmers are assigned to the farm.
        Ensure every component is assigned exactly once.
        Additionally, bias spawning to ensure at least a few warriors spawn when possible.
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

        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Base: how many farm-spawns can we create
        spawns_farm = min(len(farmers) // 2, farm_wheat // 10)

        # We will attempt to reserve some wheat for possible warrior spawns
        idx = 0
        used_wheat = 0

        # Spawn farmers
        for _ in range(spawns_farm):
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            if f1 not in assigned:
                environment.assign_group(f1, "spawn farmer")
                assigned.add(f1)
            if f2 not in assigned:
                environment.assign_group(f2, "spawn farmer")
                assigned.add(f2)
            idx += 2
            used_wheat += 10

        # Wheat left after farmer spawns
        wheat_left = max(0, farm_wheat - used_wheat)

        # Compute possible warrior spawns given remaining farmers and wheat
        remaining_farmers_for_warrior = farmers[idx:]
        spawns_warrior = min(len(remaining_farmers_for_warrior) // 2, wheat_left // 12)

        # If no warrior spawn possible but there are enough resources to spawn one pair,
        # adjust to spawn at least one warrior by reallocating one pair from farmers spawns if possible.
        if spawns_warrior == 0 and spawns_farm > 0:
            # Check if we can free one farm-pair and still have 12 wheat
            if len(farmers) >= 4 and wheat_left >= 12:
                # Move one pair from farm-spawns to warrior-spawns
                spawns_farm -= 1
                used_wheat -= 10
                wheat_left += 10
                spawns_warrior = 1
                # Reassign the two farmers from the farm-spawn to warrior-spawn
                # The two farmers for the freed pair are at indices (idx-2) and (idx-1) originally
                # Reassign them if not already assigned
                f1 = farmers[idx - 2]
                f2 = farmers[idx - 1]
                if f1 not in assigned:
                    environment.assign_group(f1, "spawn warrior")
                    assigned.add(f1)
                if f2 not in assigned:
                    environment.assign_group(f2, "spawn warrior")
                    assigned.add(f2)

        # Spawn warriors (new or from remaining pool)
        for _ in range(spawns_warrior):
            f1 = farmers[idx]
            f2 = farmers[idx + 1]
            if f1 not in assigned:
                environment.assign_group(f1, "spawn warrior")
                assigned.add(f1)
            if f2 not in assigned:
                environment.assign_group(f2, "spawn warrior")
                assigned.add(f2)
            idx += 2
            wheat_left = max(0, wheat_left - 12)

        # Remaining farmers go to farm
        for j in range(idx, len(farmers)):
            f = farmers[j]
            if f not in assigned:
                environment.assign_group(f, "farm")
                assigned.add(f)

        # Safety: assign any component not yet assigned (defensive)
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(c)

    def assign_in_cave(self, components: List, environment, group_ids, step: int):
        """
        In the cave:
        - Warriors go to the attack; Farmers go to the village.
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")

        # No extra assignments needed; this block covers all cave villagers.