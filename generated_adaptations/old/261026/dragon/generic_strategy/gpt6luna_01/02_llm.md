The strategy sends every Warrior to the Cave and has them attack as soon as possible; Farmers remain in the Village to produce wheat, except for pairs assigned to spawning. It tracks spawn attempts and prioritizes producing the requested two Farmers and two Warriors, then uses surplus wheat to spawn more Warriors. Every component is explicitly assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_attempts = {"spawn farmer": 0, "spawn warrior": 0}
        self._last_spawn_step = None

    @staticmethod
    def _group_id(group_ids, name):
        if isinstance(group_ids, dict):
            return group_ids[name]
        for group_id in group_ids:
            if group_id == name or str(group_id) == name:
                return group_id
        return name

    def _assign(self, environment, component, group_ids, name):
        environment.assign_group(component, self._group_id(group_ids, name))

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Spawn one batch at most per step, and only when there are two
        # villagers available and enough wheat.
        spawn_group = None
        if self._last_spawn_step != step and len(farmers) >= 2:
            wheat = environment.farm.wheat

            if self._spawn_attempts["spawn warrior"] < 2 and wheat >= 12:
                spawn_group = "spawn warrior"
            elif self._spawn_attempts["spawn farmer"] < 2 and wheat >= 10:
                spawn_group = "spawn farmer"
            elif wheat >= 12 and len(farmers) >= 3:
                # Once the minimum targets are met, grow the Warrior force
                # while leaving at least one Farmer to work.
                spawn_group = "spawn warrior"

        spawn_pair = set()
        if spawn_group is not None:
            spawn_pair = set(farmers[:2])
            self._spawn_attempts[spawn_group] += 1
            self._last_spawn_step = step

        for component in components:
            if component.role == "Warrior":
                self._assign(environment, component, group_ids, "cave")
            elif component in spawn_pair:
                self._assign(environment, component, group_ids, spawn_group)
            else:
                self._assign(environment, component, group_ids, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for component in components:
            if component.role == "Warrior":
                # Attack immediately while the Dragon is alive; avoid needless
                # combat after it has been defeated.
                group = "attack" if dragon_alive else "cave"
            else:
                # Farmers belong in the Village to produce wheat or spawn.
                group = "village"
            self._assign(environment, component, group_ids, group)
```