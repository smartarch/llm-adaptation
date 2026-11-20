The main change is to use **every eligible farmer pair** for spawning when wheat allows, rather than limiting each turn to one pair. I’d first grow the farming workforce, then spend surplus wheat on multiple warrior spawns while leaving at least one farmer to produce food. Meals take priority, and Cave warriors make staggered trips back to eat so the Dragon is less likely to get a regeneration turn.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._extra_farmers_requested = 0
        self._extra_warriors_requested = 0
        self._initial_farmer_count = None
        self._farmer_target = 4
        self._warrior_spawn_target = 10

    @staticmethod
    def _role(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _group_id(group_ids, name):
        for group_id in group_ids:
            if group_id == name or str(group_id) == name:
                return group_id
        return name

    def _assign(self, environment, component, group_ids, name):
        environment.assign_group(
            component,
            self._group_id(group_ids, name),
        )

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        farmers = [c for c in components if self._role(c) == "farmer"]
        warriors = [c for c in components if self._role(c) == "warrior"]

        if self._initial_farmer_count is None:
            self._initial_farmer_count = len(farmers)

        assigned = set()

        # Feed villagers before they are at risk of starvation. A warrior
        # who is due for food should eat before making another trip to the Cave.
        meal_candidates = [
            c for c in components
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        meal_candidates.sort(
            key=lambda c: (
                -getattr(c, "steps_since_meal", 0),
                0 if self._role(c) == "warrior" else 1,
            )
        )

        for c in meal_candidates:
            if wheat <= 0:
                break
            self._assign(environment, c, group_ids, "eat")
            assigned.add(id(c))
            wheat -= 1

        available_farmers = [
            c for c in farmers
            if id(c) not in assigned
            and getattr(c, "steps_since_meal", 0) < 4
        ]

        # Build a modest farming base first, then direct the same workforce
        # toward producing warriors. Each assigned pair can contribute a spawn.
        farmer_goal = max(
            0,
            self._farmer_target - self._initial_farmer_count,
        )
        spawn_group = None
        spawn_cost = 0

        if self._extra_farmers_requested < farmer_goal:
            spawn_group, spawn_cost = "spawn farmer", 10

        reserve = min(12, max(4, len(components) // 2))

        if (
            spawn_group is not None
            and len(available_farmers) >= 2
            and wheat >= spawn_cost + reserve
        ):
            for c in available_farmers[:2]:
                self._assign(environment, c, group_ids, spawn_group)
                assigned.add(id(c))
            self._extra_farmers_requested += 1

        else:
            remaining = [
                c for c in available_farmers
                if id(c) not in assigned
            ]

            # Spawn as many warriors as the current food reserve supports,
            # while keeping at least one farmer working whenever possible.
            if self._extra_warriors_requested < self._warrior_spawn_target:
                max_pairs = max(0, (len(remaining) - 1) // 2)
                affordable_pairs = max(0, (wheat - reserve) // 12)
                remaining_spawns = (
                    self._warrior_spawn_target
                    - self._extra_warriors_requested
                )
                pairs = min(max_pairs, affordable_pairs, remaining_spawns)

                for i in range(pairs * 2):
                    c = remaining[i]
                    self._assign(environment, c, group_ids, "spawn warrior")
                    assigned.add(id(c))
                self._extra_warriors_requested += pairs

        for c in components:
            if id(c) in assigned:
                continue

            if self._role(c) == "warrior":
                if getattr(c, "steps_since_meal", 0) >= 4:
                    group = "eat" if wheat > 0 else "farm"
                    if group == "eat":
                        wheat -= 1
                else:
                    group = "cave"
            else:
                group = "farm"

            self._assign(environment, c, group_ids, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = getattr(environment.dragon, "hp", 0)

        warriors = [c for c in components if self._role(c) == "warrior"]
        non_warriors = [c for c in components if self._role(c) != "warrior"]

        # Return some warriors at meal age 3 and all remaining due warriors
        # by age 4. This staggers meal trips without letting anyone get too
        # close to the starvation threshold.
        for index, c in enumerate(warriors):
            age = getattr(c, "steps_since_meal", 0)

            if dragon_hp <= 0:
                group = "cave"
            elif age >= 4 or (age >= 3 and index % 2 == 0):
                group = "village"
            else:
                group = "attack"

            self._assign(environment, c, group_ids, group)

        for c in non_warriors:
            self._assign(environment, c, group_ids, "village")
```