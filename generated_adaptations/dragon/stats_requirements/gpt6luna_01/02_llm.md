The strategy keeps farmers in the Village to produce food, while sending fed warriors to the Cave and attacking whenever they are healthy enough to do so. It prioritizes meals before spawning, returns Cave warriors to the Village when they need food, and uses pairs of available villagers to spawn two warriors and then a farmer when wheat permits. Spawn counts are tracked across calls so the strategy does not repeatedly spend resources on the same target.

```py
import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _group(name, group_ids):
        # Return the exact valid group ID supplied by the environment.
        return name if name in group_ids else next(
            group_id for group_id in group_ids if str(group_id) == name
        )

    def _assign(self, environment, component, name, group_ids):
        environment.assign_group(component, self._group(name, group_ids))

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()
        wheat = max(0, int(environment.farm.wheat))

        # Warriors should eat before their hunger reaches the point where they
        # must leave the Village; farmers eat with a little more margin.
        meal_candidates = [
            c for c in components
            if (
                (self._role(c) == "warrior" and c.steps_since_meal >= 3)
                or (self._role(c) == "farmer" and c.steps_since_meal >= 4)
            )
        ]
        meal_candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # Spend available wheat on the villagers with the most urgent need.
        for component in meal_candidates:
            if wheat > 0:
                self._assign(environment, component, "eat", group_ids)
                assigned.add(id(component))
                wheat -= 1

        # If food is unavailable, keep hungry villagers in the Village rather
        # than sending hungry warriors to the Cave.
        for component in components:
            if id(component) in assigned:
                continue
            if (
                self._role(component) == "warrior"
                and component.steps_since_meal >= 3
            ):
                self._assign(environment, component, "farm", group_ids)
                assigned.add(id(component))

        available = [c for c in components if id(c) not in assigned]
        available.sort(key=lambda c: 0 if self._role(c) == "farmer" else 1)

        # Spawn only when two villagers are available and wheat covers the
        # spawn cost. Warriors are the first priority, followed by one farmer.
        spawn_group = None
        spawn_cost = 0
        if self._warrior_spawn_requests < 2:
            spawn_group = "spawn warrior"
            spawn_cost = 12
        elif self._farmer_spawn_requests < 1:
            spawn_group = "spawn farmer"
            spawn_cost = 10

        if spawn_group is not None and len(available) >= 2 and wheat >= spawn_cost:
            for component in available[:2]:
                self._assign(environment, component, spawn_group, group_ids)
                assigned.add(id(component))

            # The pair and wheat threshold were checked before assigning.
            if spawn_group == "spawn warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        dragon_alive = environment.dragon.hp > 0

        # Assign every remaining villager explicitly. Farmers remain in the
        # Village; fed warriors head to the Cave while the Dragon is alive.
        for component in components:
            if id(component) in assigned:
                continue

            if self._role(component) == "farmer" or not dragon_alive:
                group = "farm"
            elif component.steps_since_meal >= 3:
                # Avoid sending a warrior away when it is due to eat.
                group = "farm"
            else:
                group = "cave"

            self._assign(environment, component, group, group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for component in components:
            if not dragon_alive:
                group = "village"
            elif self._role(component) != "warrior":
                # Farmers should stay in the Village.
                group = "village"
            elif component.steps_since_meal >= 4:
                # Moving takes one step, leaving time to eat before starvation.
                group = "village"
            else:
                # Keep attacking whenever the warrior is healthy enough to deal
                # damage, preventing the Dragon from regenerating.
                group = "attack"

            self._assign(environment, component, group, group_ids)
```