The strategy keeps all existing warriors moving toward the Cave and assigns every warrior there to attack; farmers stay in the Village. When there is enough wheat, it temporarily assigns a pair of farmers to a spawn group, first aiming to spawn two farmers and then three warriors. All other farmers are explicitly assigned to farm, and every component is reassigned on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_pairs = 0
        self.warrior_spawn_pairs = 0
        self.last_spawn_step = None
        self.cave_warrior_count = 0

    @staticmethod
    def _is_role(component, role):
        return str(getattr(component, "role", "")).lower() == role.lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if self._is_role(c, "Farmer")]
        warriors = [c for c in components if self._is_role(c, "Warrior")]

        # Existing warriors always head to the Cave.
        for component in warriors:
            environment.assign_group(component, "cave")

        spawn_group = None
        wheat = getattr(environment.farm, "wheat", 0)

        # Use at most one spawn pair per step. Spawn a small farmer reserve
        # first, then prioritize adding warriors for Dragon damage.
        can_spawn = (
            self.last_spawn_step != step
            and len(farmers) >= 2
        )
        if can_spawn:
            if self.farmer_spawn_pairs < 2 and wheat >= 10:
                spawn_group = "spawn farmer"
                self.farmer_spawn_pairs += 1
            elif self.warrior_spawn_pairs < 3 and wheat >= 12:
                spawn_group = "spawn warrior"
                self.warrior_spawn_pairs += 1

        if spawn_group is not None:
            self.last_spawn_step = step
            for component in farmers[:2]:
                environment.assign_group(component, spawn_group)
            farmers = farmers[2:]

        # Every farmer not assigned to a spawn group remains in the Village
        # and works the farm.
        for component in farmers:
            environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        self.cave_warrior_count = sum(
            1 for component in components if self._is_role(component, "Warrior")
        )

        for component in components:
            if self._is_role(component, "Warrior"):
                environment.assign_group(component, "attack")
            else:
                # Farmers belong in the Village, not in the Cave.
                environment.assign_group(component, "village")
```