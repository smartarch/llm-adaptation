from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawned = False
        self._warrior_spawns = 0
        self._warrior_spawn_target = 5

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
        assigned = set()

        farmers = [c for c in components if self._role(c) == "farmer"]
        warriors = [c for c in components if self._role(c) == "warrior"]

        # Warriors in the Village should eat before returning to the Cave.
        # Feed farmers nearing the starvation threshold as well.
        hungry = []
        for c in warriors:
            if getattr(c, "steps_since_meal", 0) >= 3:
                hungry.append(c)
        for c in farmers:
            if getattr(c, "steps_since_meal", 0) >= 5:
                hungry.append(c)

        hungry.sort(
            key=lambda c: (
                -getattr(c, "steps_since_meal", 0),
                0 if self._role(c) == "warrior" else 1,
            )
        )

        for c in hungry:
            if wheat <= 0:
                break
            self._assign(environment, c, group_ids, "eat")
            assigned.add(id(c))
            wheat -= 1

        # Feed farmers before they reach the starvation threshold when food
        # is available, prioritizing those with the oldest meal timers.
        farmers_due = sorted(
            (
                c for c in farmers
                if id(c) not in assigned
                and getattr(c, "steps_since_meal", 0) >= 4
            ),
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        )
        for c in farmers_due:
            if wheat <= 0:
                break
            self._assign(environment, c, group_ids, "eat")
            assigned.add(id(c))
            wheat -= 1

        # Spawn a farmer first, then spawn warriors. Keep some wheat available
        # for meals, and leave at least two farmers working whenever possible.
        spawn_group = None
        spawn_cost = 0
        if not self._farmer_spawned:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif self._warrior_spawns < self._warrior_spawn_target:
            spawn_group, spawn_cost = "spawn warrior", 12

        available_farmers = [
            c for c in farmers
            if id(c) not in assigned
            and getattr(c, "steps_since_meal", 0) < 4
        ]

        meal_reserve = min(8, max(3, len(components) // 2))
        if (
            spawn_group is not None
            and len(available_farmers) >= 2
            and wheat >= spawn_cost + meal_reserve
        ):
            for c in available_farmers[:2]:
                self._assign(environment, c, group_ids, spawn_group)
                assigned.add(id(c))

            if spawn_group == "spawn farmer":
                self._farmer_spawned = True
            else:
                self._warrior_spawns += 1

        for c in components:
            if id(c) in assigned:
                continue

            if self._role(c) == "warrior":
                # A warrior who has eaten recently should go fight. Keep a
                # warrior with a due meal in the Village if no wheat was
                # available to feed them this turn.
                if getattr(c, "steps_since_meal", 0) >= 3:
                    group = "farm"
                else:
                    group = "cave"
            else:
                group = "farm"

            self._assign(environment, c, group_ids, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "warrior"
        ]

        # Stagger meal trips so the entire attacking force is less likely to
        # leave the Cave on the same turn. At age 4 everyone still due returns.
        for index, c in enumerate(warriors):
            age = getattr(c, "steps_since_meal", 0)

            if age >= 4:
                group = "village"
            elif age >= 3 and index % 2 == 0:
                group = "village"
            else:
                group = "attack"

            self._assign(environment, c, group_ids, group)

        # Any non-warrior in the Cave should return to the Village.
        for c in components:
            if self._role(c) != "warrior":
                self._assign(environment, c, group_ids, "village")