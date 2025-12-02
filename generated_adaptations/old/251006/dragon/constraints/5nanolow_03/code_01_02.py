from typing import List
import abc

# The base class is expected to be importable as described
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components: List, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay and farm
        - "cave": go to Cave (to join attack)
        - "spawn farmer": for every two villagers + 10 wheat, spawn a Farmer
        - "spawn warrior": for every two villagers + 12 wheat, spawn a Warrior
        """
        # Collect current counts and categorize by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers stay in village, but some go to spawn groups
        # We'll compute spawns based on current farm wheat
        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Number of farmers we can spawn as farmers (needs 2 farmers per spawn and 10 wheat per spawn)
        spawns_farm = min(len(farmers) // 2, farm_wheat // 10)

        # Assign first 2*spawns_farm farmers to spawn_farm group
        idx = 0
        for _ in range(spawns_farm):
            # take two farmers
            if idx + 2 <= len(farmers):
                self._assign_slice(farmers, idx, idx + 2, "spawn farmer", environment)
                idx += 2
        # Wheat consumed by spawn farmers
        # Remaining wheat after spawns_farm
        farm_wheat_left = max(0, farm_wheat - spawns_farm * 10)

        # Remaining farmers available for spawn warrior
        remaining_farmers_for_warrior = farmers[idx:]
        spawns_warrior = min(len(remaining_farmers_for_warrior) // 2, farm_wheat_left // 12)

        # Assign the first 2*spawns_warrior from remaining to spawn_warrior
        if spawns_warrior > 0:
            end = idx + 2 * spawns_warrior
            self._assign_slice(farmers, idx, end, "spawn warrior", environment)
            idx = end

        # Any leftover farmers go to the farm group
        remaining_farmers = farmers[idx:]
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # Ensure the groups exist (optional safety)
        for c in components:
            # If not already assigned (e.g., some edge case), default to farm
            # This keeps components always assigned to a valid group
            if not self._has_group_assigned(c, environment):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components: List, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Warriors attack Dragon
        - "cave": stay in Cave
        - "village": go to Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in Village
                environment.assign_group(c, "village")

        # Defensive: if any component somehow not assigned, place in village
        for c in components:
            if not self._is_assigned(c, environment):
                environment.assign_group(c, "village")

    # Helpers
    def _assign_slice(self, lst: List, start: int, end: int, group_name: str, environment):
        for i in range(start, min(end, len(lst))):
            environment.assign_group(lst[i], group_name)

    def _has_group_assigned(self, component, environment) -> bool:
        # Depending on the environment API, you might check the current group.
        # Here we assume if the environment has a way to query, it would be used.
        # As a fallback, return True to avoid double-assigning.
        return True

    def _is_assigned(self, component, environment) -> bool:
        # Placeholder for checking assignment; depends on environment API.
        return False