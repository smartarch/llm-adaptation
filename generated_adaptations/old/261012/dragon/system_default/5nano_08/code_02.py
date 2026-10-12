from __future__ import annotations
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (for Warriors to attack later)
        - spawn farmer: for every two villagers assigned here and 10 wheat, a new Farmer spawns
        - spawn warrior: for every two villagers assigned here and 12 wheat, a new Warrior spawns

        Strategy:
        - All Warriors go to the Cave (assigned to "cave").
        - Farmers default to "farm".
        - If enough wheat, assign up to two Farmers to "spawn farmer".
        - If enough wheat and enough Farmers remain, assign up to two additional Farmers to "spawn warrior".
        - Remaining Farmers stay in "farm".
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all Farmers -> farm
        for f in farmers:
            environment.assign_group(f, "farm")

        # Warriors in village step go to cave (to travel to the cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn planning based on wheat
        wheat = getattr(environment.farm, "wheat", 0)

        # Decide SPF (spawn farmer) count
        SPF_count = 2 if (len(farmers) >= 2) and (wheat >= 10) else 0
        # Decide SPW (spawn warrior) count
        # Needs enough farmers left after SPF and enough wheat
        remaining_after_spf = len(farmers) - SPF_count
        SPW_count = 2 if (remaining_after_spf >= 2) and (wheat >= 12) else 0

        # Assign first SPF_count farmers to "spawn farmer"
        for idx, f in enumerate(farmers):
            if idx < SPF_count:
                environment.assign_group(f, "spawn farmer")
            # Next SPW_count farmers to "spawn warrior"
            elif SPF_count <= idx < SPF_count + SPW_count:
                environment.assign_group(f, "spawn warrior")
            # The rest stay in farm (already assigned)

        # Done for village
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go back to the Village

        Strategy:
        - All Warriors -> attack
        - Farmers -> village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")