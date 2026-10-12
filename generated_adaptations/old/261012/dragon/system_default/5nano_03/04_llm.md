Reasoning about the fix

Root cause:
- The spawn groups consume wheat. In the previous implementation, spawns were decided using fixed wheat checks (10 for a spawn farmer, 12 for a spawn warrior) without accounting for the wheat already allocated to other spawns in the same village step. This could lead to situations where we attempted to assign a Farmer to a spawn warrior even though there wasn’t enough wheat left after considering prior spawns, triggering the “Not enough wheat to spawn new villager” error. Additionally, if wheat wasn’t sufficient for any spawn, some Farmers could end up not being assigned at all.

Strategy to fix:
- Track wheat as a local, mutable budget within the assign_in_village step. Each time we spawn a villager, deduct the corresponding wheat cost from this local budget.
- Perform spawns in a deterministic order:
  - First, attempt to spawn up to two Farmers (cost 10 wheat total) using the first two unassigned Farmers.
  - Then, attempt to spawn up to two Warriors (cost 12 wheat total) using the next two unassigned Farmers.
- After attempting spawns, assign all remaining unassigned Farmers to the "farm" group.
- Always assign Warriors in the village to the "cave" group (they will go to the Cave).
- In the cave, keep Farmers in the Village (as required).

This ensures:
- Wheat budget is respected for all spawn actions in the same step.
- Every Farmer is assigned to exactly one group.
- The test cases that previously failed due to wheat budgeting should now pass.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (to attack in the next phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Wheat budget (local) from the Farm (read-only in environment, but we track ourselves)
        wheat_available = 0
        try:
            wheat_available = environment.farm.wheat
        except Exception:
            wheat_available = 0

        # 3) Spawn logic with incremental wheat deduction
        next_idx = 0  # index of the next unassigned farmer
        # Try to spawn up to two Farmers (cost 10 wheat total)
        if len(farmers) - next_idx >= 2 and wheat_available >= 10:
            environment.assign_group(farmers[next_idx], "spawn farmer")
            environment.assign_group(farmers[next_idx + 1], "spawn farmer")
            next_idx += 2
            wheat_available -= 10

        # Try to spawn up to two Warriors (cost 12 wheat total) using next unassigned farmers
        if len(farmers) - next_idx >= 2 and wheat_available >= 12:
            environment.assign_group(farmers[next_idx], "spawn warrior")
            environment.assign_group(farmers[next_idx + 1], "spawn warrior")
            next_idx += 2
            wheat_available -= 12

        # 4) Remaining farmers stay in farming role
        for i in range(next_idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # Note: Any farmers not explicitly assigned by above logic will default to the last assigned group.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: attack with Warriors; move Farmers back to Village
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(comp, "village")
```