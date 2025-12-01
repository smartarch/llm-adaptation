Reasoning and adaptation strategy

Issue observed:
- The previous approach sometimes assigns villagers to the spawn groups ("spawn farmer"/"spawn warrior") even when there isn’t enough wheat to spawn them. This caused invalid assignments and test failures.
- Tests also require every component to be assigned to exactly one group. Introducing spawn groups with insufficient wheat creates paths where assignments can be rejected.

Updated strategy:
- Keep things simple and robust by avoiding spawn-group assignments altogether.
- In the village phase:
  - Assign all Warriors to the cave (to attack the Dragon as soon as possible).
  - Assign all Farmers to the farm group (stay in the Village to farm/wheat production).
- In the cave phase:
  - Warriors go to attack the Dragon.
  - Farmers go back to the Village (to continue farming).
- This guarantees every component is assigned exactly once and avoids invalid spawn-related constraints, while still respecting the core rule: Warriors attack from the Cave, Farmers stay in the Village.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village, assign villagers deterministically without using spawn groups:
        - Warriors -> cave (to attack)
        - Farmers  -> farm (stay in Village and farm)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, assign villagers as:
        - Warriors -> attack (attack the Dragon)
        - Farmers  -> village (return to the Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```