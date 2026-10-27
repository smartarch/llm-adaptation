The previous version used a `set` of component objects to track returning Warriors; if those objects are unhashable, the strategy can fail before making assignments. This version avoids that and keeps the schedule simple: Warriors return to eat before starvation, with staggered departures when possible; fed Warriors in the Village head back to attack. Farmers eat before starvation, and spawning is attempted only when a pair and enough wheat are available.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _assign(environment, component, group, group_ids):
        if group not in group_ids:
            raise ValueError(f"Group {group!r} is not available")
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_this_turn = 0

        for component in components:
            if component.role == "Warrior":
                if component.steps_since_meal >= 4:
                    self._assign(environment, component, "eat", group_ids)
                    meals_this_turn += 1
                else:
                    self._assign(environment, component, "cave", group_ids)
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat", group_ids)
                meals_this_turn += 1
            else:
                farmers.append(component)

        # Avoid spending wheat needed for meals. Try to create Warriors first,
        # then Farmers, as long as a pair of Farmers can be assigned.
        wheat = environment.farm.wheat
        plans = []
        if self._warrior_spawn_requests < 2:
            plans.append(("spawn warrior", 12, "warrior"))
        if self._farmer_spawn_requests < 2:
            plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in plans:
            if len(farmers) < 2 or wheat < cost + meals_this_turn + 1:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for component in pair:
                self._assign(environment, component, group, group_ids)

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        for component in farmers:
            self._assign(environment, component, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []
        for component in components:
            if component.role == "Warrior":
                warriors.append(component)
            else:
                self._assign(environment, component, "village", group_ids)

        # At four steps without food, stagger departures by list position.
        # At five, send everyone who needs food back rather than risk starvation.
        for index, component in enumerate(warriors):
            hungry = component.steps_since_meal
            return_to_village = (
                hungry >= 5
                or (hungry >= 4 and (index + step) % 2 == 0)
            )

            if return_to_village:
                self._assign(environment, component, "village", group_ids)
            else:
                self._assign(environment, component, "attack", group_ids)
```