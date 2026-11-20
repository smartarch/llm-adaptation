The main change is to stop putting an arbitrary cap on warrior production or delaying spawns behind a large wheat reserve. Spawn one farmer when affordable, then use available farmer pairs to spawn warriors whenever there is enough wheat; meanwhile, send every healthy warrior toward the Cave. Warriors in the Cave return early enough to eat without starving, and warriors in the Village eat before setting out again.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_requested = False
        self._warrior_spawn_requests = 0

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _group_id(name, group_ids):
        for group_id in group_ids:
            if str(group_id) == name:
                return group_id
        return name

    def _assign(self, environment, component, name, group_ids):
        environment.assign_group(
            component, self._group_id(name, group_ids)
        )

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()
        wheat = max(0, int(environment.farm.wheat))
        dragon_alive = environment.dragon.hp > 0

        # Feed warriors before sending them away, and feed farmers before
        # starvation. Prioritize the most urgent meals if wheat is limited.
        meal_candidates = sorted(
            (
                c for c in components
                if (
                    (self._role(c) == "warrior" and c.steps_since_meal >= 3)
                    or (self._role(c) == "farmer" and c.steps_since_meal >= 5)
                )
            ),
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for component in meal_candidates:
            if wheat <= 0:
                break
            self._assign(environment, component, "eat", group_ids)
            assigned.add(id(component))
            wheat -= 1

        # Prefer spawning the required farmer once. After that, turn surplus
        # wheat into warriors, using farmers for the spawn pair where possible.
        farmers = [
            c for c in components
            if id(c) not in assigned and self._role(c) == "farmer"
        ]

        spawn_pair = None
        spawn_group = None

        if (
            dragon_alive
            and not self._farmer_spawn_requested
            and len(farmers) >= 2
            and wheat >= 10
        ):
            spawn_pair = farmers[:2]
            spawn_group = "spawn farmer"
        elif dragon_alive and len(farmers) >= 2 and wheat >= 12:
            spawn_pair = farmers[:2]
            spawn_group = "spawn warrior"
        elif (
            dragon_alive
            and self._warrior_spawn_requests < 2
            and wheat >= 12
        ):
            # If there are not two farmers available, use any two villagers
            # still in the Village to meet the minimum warrior-spawn target.
            others = [
                c for c in components
                if id(c) not in assigned and c not in farmers
            ]
            candidates = farmers + others
            if len(candidates) >= 2:
                spawn_pair = candidates[:2]
                spawn_group = "spawn warrior"

        if spawn_pair is not None:
            for component in spawn_pair:
                self._assign(environment, component, spawn_group, group_ids)
                assigned.add(id(component))

            if spawn_group == "spawn farmer":
                self._farmer_spawn_requested = True
            else:
                self._warrior_spawn_requests += 1

        # Explicitly assign every other villager. Farmers work; warriors head
        # to the Cave as soon as they have eaten recently enough.
        for component in components:
            if id(component) in assigned:
                continue

            if not dragon_alive:
                group = "farm"
            elif self._role(component) == "farmer":
                group = "farm"
            elif component.steps_since_meal >= 3:
                # If a meal was not available above, do not send a hungry
                # warrior on a trip that would make it miss another meal.
                group = "farm"
            else:
                group = "cave"

            self._assign(environment, component, group, group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for component in components:
            if not dragon_alive or self._role(component) != "warrior":
                group = "village"
            elif component.steps_since_meal >= 4:
                # Return before starvation; after reaching the Village the
                # warrior can eat on its next assignment.
                group = "village"
            else:
                group = "attack"

            self._assign(environment, component, group, group_ids)
```