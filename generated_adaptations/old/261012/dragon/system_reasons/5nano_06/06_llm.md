Reasoning and updated adaptation strategy

Root cause of failures:
- The previous implementation could attempt to assign some farmers to both spawn groups in the same step or in scenarios where wheat is insufficient for the planned spawns, leading to tests complaining about not enough wheat or multiple assignments for the same villager.
- Additionally, some farmers were not getting assigned in assign_in_village, triggering the “not assigned” errors.

Updated strategy:
- Perform a single-pass, one-shot assignment in assign_in_village to ensure every villager is assigned to exactly one group.
- Warriors: always move to the Cave (group "cave") in the village phase.
- Farmers: decide a single allocation in the village phase:
  - If there are at least 4 farmers and at least 22 wheat, allocate:
    - first 2 farmers to "spawn farmer" (consuming 10 wheat)
    - next 2 farmers to "spawn warrior" (consuming 12 wheat)
    - any remaining farmers to "farm"
  - Else if there are at least 2 farmers and at least 10 wheat, allocate:
    - first 2 farmers to "spawn farmer"
    - remaining farmers to "farm"
  - Else (not enough wheat or not enough farmers), allocate all farmers to "farm"
- In assign_in_cave, keep Warriors in "attack" and move Farmers back to "village" (they should stay in Village).

This approach guarantees:
- No farmer is assigned to multiple groups in the same step.
- Wheat constraints are respected for possible spawns.
- All warriors end up in the cave to attack the dragon.
- Farmers stay in the village when not spawning and return to village in the cave phase.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Assign Farmers with a single-pass strategy (to avoid repeated assignments)
        if not farmers:
            return

        total_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Case A: spawn both farmer and warrior, if enough farmers and wheat
        if len(farmers) >= 4 and total_wheat >= 22:
            # First 2 -> spawn farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Next 2 -> spawn warrior
            for c in farmers[2:4]:
                environment.assign_group(c, "spawn warrior")
            # Remaining farmers (if any) stay in farm
            for c in farmers[4:]:
                environment.assign_group(c, "farm")

        # Case B: only spawn farmer if enough wheat and at least 2 farmers
        elif len(farmers) >= 2 and total_wheat >= 10:
            # First 2 -> spawn farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Remaining farmers stay in farm
            for c in farmers[2:]:
                environment.assign_group(c, "farm")

        # Case C: not enough wheat or not enough farmers - all stay farming
        else:
            for c in farmers:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            elif getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "village")
```