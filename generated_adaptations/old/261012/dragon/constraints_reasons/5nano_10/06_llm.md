Reasoning and updated adaptation strategy

What was wrong
- The previous approach could attempt to assign the same Farmer to multiple spawn groups in one step or attempt to spawn warriors even when there wasn’t enough wheat left after considering possible farmer spawns. This caused invalid group assignments and test failures.
- Tests require every component to be assigned exactly once per step. We must ensure non-overlapping, single-group assignment for each Farmer, while still attempting to spawn new villagers when resources allow.

Updated strategy
- In assign_in_village:
  - Move all Warriors to the cave (attack-ready).
  - For Farmers, decide non-overlapping spawn candidates:
    - If there are at least 2 Farmers and wheat >= 10, pick the first two Farmers to spawn a new Farmer (spawn farmer) and deduct 10 wheat logically (to prevent over-commitment in the same step).
    - From the remaining unassigned Farmers, if there are at least 2 and the remaining wheat >= 12, pick the next two to spawn a Warrior (spawn warrior) and deduct 12 wheat.
  - Any Farmer not assigned to a spawn group goes to the "farm" group.
  - All Warriors go to the "cave" group.
- In assign_in_cave:
  - Warriors attack; Farmers go back to the Village.

This guarantees:
- Every component is assigned exactly once.
- Spawn actions are only attempted when there is enough wheat (including a simple check to avoid overlapping spawns in the same step).
- All Warriors are in the Cave, providing early Dragon pressure, with spawning boosting future DPS.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Track assignments to ensure each farmer is assigned exactly once
        assigned = {f: None for f in farmers}

        # 1) Spawn a Farmer if possible (needs 2 farmers and >= 10 wheat)
        if len(farmers) >= 2 and wheat >= 10:
            f1, f2 = farmers[0], farmers[1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned[f1] = "spawn farmer"
            assigned[f2] = "spawn farmer"
            wheat -= 10

        # 2) Spawn a Warrior if possible from remaining unassigned farmers
        remaining = [f for f in farmers if assigned.get(f) is None]
        if len(remaining) >= 2 and wheat >= 12:
            w1, w2 = remaining[0], remaining[1]
            environment.assign_group(w1, "spawn warrior")
            environment.assign_group(w2, "spawn warrior")
            assigned[w1] = "spawn warrior"
            assigned[w2] = "spawn warrior"
            wheat -= 12

        # 3) Assign all other farmers to farming
        for f in farmers:
            if assigned.get(f) is None:
                environment.assign_group(f, "farm")

        # 4) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should return to Village
        for v in components:
            if getattr(v, "role", None) == "Warrior":
                environment.assign_group(v, "attack")
            else:
                environment.assign_group(v, "village")
```