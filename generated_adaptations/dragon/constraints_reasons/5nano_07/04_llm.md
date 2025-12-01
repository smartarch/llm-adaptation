Reasoning and adaptation strategy ( Updated )

Root cause of failures:
- The previous implementation assigned some villagers to a spawn group and then re-assigned them again within the same assign_in_village call. This caused multiple assignments for the same component (test_no_repeated_assignments fails).
- The strategy also attempted to do multiple passes to split farmers into farm/spawn groups, which violated the “one group per component” constraint.

Updated strategy:
- Do a single, deterministic pass over all villagers in assign_in_village, assigning exactly one group per component.
- Rules enforced in one pass:
  - All Warriors go to the Cave (group "cave") in village phase; they will be moved to attack in the cave phase.
  - All Farmers default to Farm (group "farm") to keep wheat production.
  - Spawn groups are optional augmentations of the same villagers, but to avoid multiple assignments, they are decided in this single pass:
    - If there are at least 4 farmers and at least 10 wheat, assign two of them to "spawn farmer" to spawn a new Farmer.
    - If after that there are at least two remaining farmers and at least 12 wheat, assign two more to "spawn warrior" to spawn a new Warrior.
  - If not enough wheat or not enough farmers, skip spawning to avoid wasted assignments.
- In assign_in_cave, keep the rule: all Warriors attack (group "attack"), Farmers go to "village" (they stay in village or return there).

This preserves the “one assignment per component” constraint, ensures early dragon attack by Warriors, keeps Farmers in the village, and provides gradual spawning to increase DPS across steps.

Python code (single class implementation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be re-assigned to attack in assign_in_cave)
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, spawn a Warrior
        """
        # Collect farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare single-pass assignment mapping
        assignment = {}

        # 1) Warriors go to cave (they will attack later)
        for w in warriors:
            assignment[w] = "cave"

        # 2) Farmers default to farming
        for f in farmers:
            assignment[f] = "farm"

        # 3) Wheat available in farm (guard against missing attribute)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        # 4) Attempt spawning decisions (single-pass, non-overlapping)
        # If we have at least 4 farmers and enough wheat, allocate two to spawn a farmer
        if len(farmers) >= 4 and wheat >= 10:
            to_spawn_farm = farmers[:2]
            for f in to_spawn_farm:
                assignment[f] = "spawn farmer"

            # Remaining farmers (at least 2) may spawn a warrior if wheat allows
            remaining = [f for f in farmers if f not in to_spawn_farm]
            if len(remaining) >= 2 and wheat >= 22:
                to_spawn_war = remaining[:2]
                for f in to_spawn_war:
                    assignment[f] = "spawn warrior"

        # If we couldn't spawn farmer but we can spawn a warrior using 4 farmers total
        elif len(farmers) >= 4 and wheat >= 12:
            remaining = farmers[:4]
            to_spawn_war = remaining[:2]
            for f in to_spawn_war:
                assignment[f] = "spawn warrior"

        # Apply the single-pass assignments
        for comp, grp in assignment.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```