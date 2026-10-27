I’d avoid sending every Warrior back as soon as they become hungry: synchronized meal trips can leave the Dragon untouched for several turns. This version staggers returns where possible, sends Warriors back before starvation makes them ineffective, and spawns only when a full pair and the wheat cost are available. It explicitly assigns every component on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _assign(environment, component, group, group_ids):
        if group in group_ids:
            environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_assigned = 0

        for component in components:
            if component.role == "Warrior":
                if component.steps_since_meal >= 5:
                    self._assign(environment, component, "eat", group_ids)
                    meals_assigned += 1
                else:
                    self._assign(environment, component, "cave", group_ids)
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat", group_ids)
                meals_assigned += 1
            else:
                farmers.append(component)

        # Leave wheat for assigned meals and a small reserve.
        wheat_available = max(
            0, environment.farm.wheat - meals_assigned - 2
        )

        # Request Warriors first, then Farmers. Each request needs a pair.
        plans = []
        if self._warrior_spawn_requests < 2:
            plans.append(("spawn warrior", 12, "warrior"))
        if self._farmer_spawn_requests < 2:
            plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in plans:
            if len(farmers) < 2 or wheat_available < cost:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for component in pair:
                self._assign(environment, component, group, group_ids)

            wheat_available -= cost
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

        for index, component in enumerate(warriors):
            hunger = component.steps_since_meal

            # At five steps without food, return before starvation can disable
            # attacks. At four, stagger departures when multiple Warriors exist.
            return_to_village = (
                hunger >= 5
                or (
                    hunger >= 4
                    and len(warriors) > 1
                    and (index + step) % 2 == 0
                )
            )

            if return_to_village:
                self._assign(environment, component, "village", group_ids)
            else:
                self._assign(environment, component, "attack", group_ids)
```