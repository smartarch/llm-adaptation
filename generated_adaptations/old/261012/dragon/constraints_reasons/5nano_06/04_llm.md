Strategy update and reasoning

Problem with previous implementation:
- We assigned some villagers to multiple groups in a single step (e.g., sending farmers to both “farm” and “spawn farmer”). This caused the “no repeated assignments” failures.

Revised strategy:
- In assign_in_village, compute a single, non-overlapping plan for every villager.
  - Warriors are planned to go to the cave (plan = "cave") since all warriors must eventually reach the cave.
  - Farmers default to plan = "farm" (stay in the village and farm).
  - If wheat allows, reassign two farmers from the “farm” plan to the “spawn farmer” plan (consuming 10 wheat). Those two farmers are no longer in the “farm” plan.
  - If wheat still allows and at least two farmers remain in the “farm” plan, reassign another two farmers to the “spawn warrior” plan (consuming 12 wheat). These farmers are no longer in the “farm” plan.
- After establishing a non-overlapping plan, assign every villager to exactly one group using environment.assign_group.
- In assign_in_cave, keep the previous logic but ensure it only reclassifies villagers present in the cave for the current step:
  - Warriors -> "attack"
  - Farmers -> "village"
  - Unknown roles -> default to "cave" (fallback)

This approach fixes the repeated-assignment failures and preserves spawning behavior while respecting the constraints that all Warriors should eventually reach the cave and that we spawn a small number of new villagers when feasible.

Code (Python)

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Build a non-overlapping plan for this step
        plan = {}

        # 1) All Warriors should go to the Cave (plan = "cave")
        for c in warriors:
            plan[c] = "cave"

        # 2) All Farmers default to "farm"
        for c in farmers:
            plan[c] = "farm"

        # Current wheat in the farm
        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 3) Spawn logic: move some farmers to spawn groups if resources allow
        # Identify farmers currently planned to farm
        farmers_to_seed_farm = [c for c in farmers if plan.get(c) == "farm"]

        # Attempt to spawn a Farmer: need 2 farmers + wheat >= 10
        if len(farmers_to_seed_farm) >= 2 and current_wheat >= 10:
            to_spawn_farmers = farmers_to_seed_farm[:2]
            for c in to_spawn_farmers:
                plan[c] = "spawn farmer"

        # After possible farmer spawn, try to spawn a Warrior with remaining farmers
        remaining_for_warrior = [c for c in farmers if plan.get(c) == "farm"]
        if len(remaining_for_warrior) >= 2 and current_wheat >= 12:
            to_spawn_warriors = remaining_for_warrior[:2]
            for c in to_spawn_warriors:
                plan[c] = "spawn warrior"

        # 4) Apply the plan: assign each component to exactly one group
        for comp, grp in plan.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep them in cave if role is unknown
                environment.assign_group(c, "cave")
```