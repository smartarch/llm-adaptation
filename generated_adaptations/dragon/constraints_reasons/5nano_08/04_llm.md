Reasoning and strategy update

Issue identified
- The previous implementation could assign the same farmer to multiple groups in assign_in_village (e.g., both "farm" and "spawn farmer"/"spawn warrior"), which violates the requirement that each component be assigned exactly once per step. This caused the “no repeated assignments” tests to fail.
- The tests also require that we spawn both farmers and warriors sometimes to increase kill probability. The previous logic was too strict (requiring 4 farmers and 22 wheat to spawn both types at once) and could result in no spawns in some seeds.

Updated strategy
- Ensure a single, explicit assignment per villager in assign_in_village by building a final map from each farmer to exactly one group. Warriors are always assigned to the cave-group in village, and will be moved to attack in the cave phase.
- Spawning logic (in village):
  - If there are at least 2 farmers and at least 12 wheat, assign two farmers to "spawn warrior" (to spawn at least one Warrior this step). Remaining farmers (if any) stay on "farm".
  - Else if there are at least 2 farmers and at least 10 wheat, assign two farmers to "spawn farmer" (to spawn at least one additional Farmer). The rest stay on "farm".
  - Otherwise, all farmers stay on "farm".
- This guarantees exactly one assignment per farmer, satisfies the constraint that all Warriors go to the Cave (via "cave" in village stage and then "attack" in cave stage), and allows incremental spawning when resources permit.
- In assign_in_cave, move Warriors to "attack" and others to "village". This ensures all Warriors attack after moving to the Cave, and Farmers return to or stay in the Village as needed.

Code changes
- Implement a single-pass, non-overlapping assignment for villagers in the village.
- Keep the cave logic straightforward to ensure no repeated assignments.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # We'll assign exactly one group per farmer.
        # Default: all farmers go to "farm"
        assign_map = {}

        for f in farmers:
            assign_map[f] = "farm"

        # All Warriors should go to the Cave (to be attacked later in cave phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Read current wheat from the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn decision: try to spawn war or farmer, but keep assignments non-overlapping
        if len(farmers) >= 2 and wheat >= 12:
            # Use first two farmers to spawn a Warrior
            f1, f2 = farmers[0], farmers[1]
            assign_map[f1] = "spawn warrior"
            assign_map[f2] = "spawn warrior"
            # Remaining farmers (if any) stay on farm
        elif len(farmers) >= 2 and wheat >= 10:
            # Use first two farmers to spawn a Farmer
            f1, f2 = farmers[0], farmers[1]
            assign_map[f1] = "spawn farmer"
            assign_map[f2] = "spawn farmer"
            # Remaining farmers stay on farm
        # else: keep all farmers on farm (already in assign_map)

        # Apply final assignments (each farmer assigned exactly once)
        for c, grp in assign_map.items():
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack the Dragon; Farmers should go to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```