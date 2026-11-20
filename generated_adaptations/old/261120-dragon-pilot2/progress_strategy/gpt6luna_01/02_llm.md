The strategy keeps Warriors attacking whenever they are fed, and sends them back to the Village at four steps without a meal so they can eat before starving. Farmers remain in the Village; meals take priority over spawning, and spawning uses only surplus wheat while leaving farm labor available. Warrior spawns are prioritized, with Farmer spawns used when the farming workforce is small. Every observed villager is explicitly assigned on every call.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_cave_count = 0

    @staticmethod
    def _assign_all(environment, assignments):
        for component, group in assignments:
            environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._last_village_count = len(villagers)

        assignments = {}
        wheat_budget = max(0, environment.farm.wheat)

        # Feed the most overdue villagers first. Warriors get priority on ties,
        # since starvation also prevents them from dealing damage.
        meal_order = sorted(
            villagers,
            key=lambda v: (
                -v.steps_since_meal,
                0 if v.role == "Warrior" else 1,
            ),
        )
        for villager in meal_order:
            meal_deadline = 4 if villager.role == "Warrior" else 5
            if villager.steps_since_meal >= meal_deadline and wheat_budget >= 1:
                assignments[villager] = "eat"
                wheat_budget -= 1

        # Warriors already in the Village should return to the Cave once fed.
        # Farmers who were not assigned a meal are candidates for work/spawning.
        available_farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]
        for villager in villagers:
            if villager.role == "Warrior" and villager not in assignments:
                assignments[villager] = "cave"

        total_population = len(villagers) + getattr(self, "_last_cave_count", 0)
        reserve = max(4, total_population)

        # Spawn Warriors in pairs when the wheat reserve remains intact, while
        # retaining at least one Farmer to keep producing food.
        spawn_candidates = available_farmers[:]
        if len(spawn_candidates) >= 3:
            usable = len(spawn_candidates) - 1
            pairs = usable // 2
            for i in range(pairs * 2):
                assignments[spawn_candidates[i]] = "spawn warrior"
            wheat_budget -= pairs * 12
            reserve += pairs

        # If the farming workforce is particularly small, invest in Farmers
        # when there is enough surplus wheat to afford the spawn and reserve.
        remaining_farmers = [
            v for v in available_farmers if v not in assignments
        ]
        farmer_count = sum(v.role == "Farmer" for v in villagers)
        if (
            farmer_count <= 2
            and len(remaining_farmers) >= 2
            and wheat_budget >= 10 + reserve
        ):
            for villager in remaining_farmers[:2]:
                assignments[villager] = "spawn farmer"
            wheat_budget -= 10
            reserve += 1

        # Do not spend the food reserve on additional spawns.
        remaining_farmers = [
            v for v in available_farmers if v not in assignments
        ]
        if len(remaining_farmers) >= 3:
            usable = len(remaining_farmers) - 1
            pairs = usable // 2
            if pairs > 0 and wheat_budget >= pairs * 12 + reserve:
                for villager in remaining_farmers[:pairs * 2]:
                    assignments[villager] = "spawn warrior"
                wheat_budget -= pairs * 12

        # Everyone else in the Village works on the farm.
        for villager in villagers:
            if villager not in assignments:
                assignments[villager] = "farm"

        self._assign_all(
            environment,
            [(villager, assignments[villager]) for villager in villagers],
        )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._last_cave_count = len(villagers)

        assignments = {}
        for villager in villagers:
            if villager.role == "Farmer":
                # Farmers are more useful producing food in the Village.
                assignments[villager] = "village"
            elif villager.steps_since_meal >= 4:
                # One step to travel home, followed by a meal on arrival,
                # avoids reaching the starvation threshold.
                assignments[villager] = "village"
            else:
                assignments[villager] = "attack"

        self._assign_all(
            environment,
            [(villager, assignments[villager]) for villager in villagers],
        )
```