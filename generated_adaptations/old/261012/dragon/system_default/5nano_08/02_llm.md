Reasoning and adaptation strategy

Goal and constraints recap
- Kill the Dragon as fast as possible within 30 steps.
- Warriors are best used for direct damage; they should end up in the Cave and Attack the Dragon.
- Farmers keep the wheat economy going in the Village and can spawn additional villagers (both Farmers and Warriors) using the spawn-grants, given enough wheat.
- Spawning rules (per step):
  - spawn farmer: for every two villagers assigned to the "spawn farmer" group and at least 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to the "spawn warrior" group and at least 12 wheat, a new Warrior is spawned.
- All villagers must be assigned to exactly one group per step.
- We have to implement this as a class SmartAdaptation with two methods: assign_in_village and assign_in_cave.

Adaptation strategy (high level)
- In assign_in_village (villagers currently in Village):
  - Warriors should go to the Cave to prepare for attacking. So assign all Warriors to the "cave" group (which means they will travel to the Cave).
  - Farmers should stay in the Village and contribute to farming or spawning new villagers. By default, put Farmers in the "farm" group to farm.
  - Use a simple resource-aware spawning plan:
    - If there are at least 2 Farmers and wheat >= 10, move two Farmers into the "spawn farmer" group to attempt to spawn additional Farmers (this increases long-term wheat production and manpower).
    - If there are enough Farmers left (at least 2 not already in spawn farmer) and wheat >= 12, move two more Farmers into the "spawn warrior" group to attempt to spawn additional Warriors for more attacking power.
  - All other Farmers remain in "farm".
  - This keeps Warriors prepared for the Dragon while enabling growth of the workforce when wheat is available.
- In assign_in_cave (villagers currently in Cave):
  - All Warriors should attack the Dragon; assign them to the "attack" group.
  - Farmers should go back to the Village; assign them to the "village" group.
  - This aligns with the rule that Warriors attack, Farmers stay to farm or spawn.

Implementation notes
- We re-assign farmers across groups each time based on simple index-based selection to avoid needing to query current assignments.
- The decision to spawn uses wheat from environment.farm.wheat. Spawns are handled by the environment as the engine processes group assignments; we only designate who should spawn and who should farm.

Python code (SmartAdaptation class)

```py
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
```