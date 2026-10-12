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
        - cave: go to the Cave (eventual attack prep)
        - spawn farmer: for every two villagers assigned here and 10 wheat, a new Farmer spawns
        - spawn warrior: for every two villagers assigned here and 12 wheat, a new Warrior spawns

        Strategy (single-pass, no repeated assignments):
        - All Warriors -> cave
        - Farmers -> allocate to spawn groups or farm in one pass
        - Determine SPF_count and SPW_count based on wheat and farmer count, considering wheat already spent by SPF
          SPF_count = 2 if there are at least 2 farmers and wheat >= 10
          remaining_wheat after SPF = wheat - SPF_count*10
          SPW_count = 2 if there are at least 2 farmers left after SPF and remaining_wheat >= 12
        - Assign first SPF_count farmers to "spawn farmer"
        - Assign next SPW_count farmers to "spawn warrior"
        - Remaining farmers -> "farm"
        - All Warriors -> "cave"
        """
        # Separate farmers and warriors in the current village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn counts with wheat-aware constraints
        SPF_count = 2 if (len(farmers) >= 2) and (wheat >= 10) else 0
        remaining_farmers = len(farmers) - SPF_count
        remaining_wheat = wheat - SPF_count * 10

        SPW_count = 2 if (remaining_farmers >= 2) and (remaining_wheat >= 12) else 0

        # Assign farmers in a single pass according to SPF/SPW counts
        for idx, f in enumerate(farmers):
            if idx < SPF_count:
                environment.assign_group(f, "spawn farmer")
            elif idx < SPF_count + SPW_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Warriors go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # All components have been assigned exactly once

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")