The previous strategy spent too much of its wheat reserve on spawning and stopped after only two warrior-spawn attempts. This version keeps meals ahead of spawning, uses farmer pairs for spawns so warriors remain available to fight, and aims to spawn up to four warriors. Warriors attack while fed, then return to the Village early enough to eat before starving.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_requested = False
        self._warrior_spawns_requested = 0
        self._extra_warrior_target = 4

    @staticmethod
    def _name(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _group(group_ids, name):
        for group_id in group_ids:
            if group_id == name or str(group_id) == name:
                return group_id
        return name

    def _assign(self, environment, component, group_ids, name):
        environment.assign_group(component, self._group(group_ids, name))

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        assigned = {}

        farmers = [c for c in components if self._name(c) == "farmer"]
        warriors = [c for c in components if self._name(c) == "warrior"]

        # Feed warriors before they leave for the Cave, and feed farmers
        # before their meal timers reach the starvation threshold.
        meal_candidates = []
        for c in warriors:
            if getattr(c, "steps_since_meal", 0) >= 3:
                meal_candidates.append(c)
        for c in farmers:
            if getattr(c, "steps_since_meal", 0) >= 4:
                meal_candidates.append(c)

        meal_candidates.sort(
            key=lambda c: (
                0 if self._name(c) == "warrior" else 1,
                -getattr(c, "steps_since_meal", 0),
            )
        )

        for c in meal_candidates:
            if wheat <= 0:
                break
            assigned[id(c)] = "eat"
            wheat -= 1

        # Use pairs of farmers for spawning. Keep a wheat reserve for meals
        # rather than spending the last food on a new villager.
        available_farmers = [
            c for c in farmers
            if id(c) not in assigned
            and getattr(c, "steps_since_meal", 0) < 4
        ]

        spawn_group = None
        spawn_cost = 0
        if not self._farmer_spawn_requested:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif self._warrior_spawns_requested < self._extra_warrior_target:
            spawn_group, spawn_cost = "spawn warrior", 12

        meal_reserve = min(
            8,
            2 + sum(
                1 for c in components
                if getattr(c, "steps_since_meal", 0) >= 3
            ),
        )

        if (
            spawn_group is not None
            and len(available_farmers) >= 2
            and wheat >= spawn_cost + meal_reserve
        ):
            # Assign exactly one pair per turn, leaving the remaining farmers
            # to produce wheat.
            for c in available_farmers[:2]:
                assigned[id(c)] = spawn_group

            if spawn_group == "spawn farmer":
                self._farmer_spawn_requested = True
            else:
                self._warrior_spawns_requested += 1

        for c in components:
            group = assigned.get(id(c))
            if group is None:
                if self._name(c) == "warrior":
                    # Send fed warriors to fight; keep hungry ones in the
                    # Village until they can eat.
                    group = (
                        "farm"
                        if getattr(c, "steps_since_meal", 0) >= 3
                        else "cave"
                    )
                else:
                    group = "farm"
            self._assign(environment, c, group_ids, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = getattr(environment.dragon, "hp", 0)

        for c in components:
            if self._name(c) != "warrior":
                group = "village"
            elif dragon_hp <= 0:
                group = "cave"
            elif getattr(c, "steps_since_meal", 0) >= 4:
                # Return early: the trip takes a step, then the warrior can
                # eat in the Village before reaching the starvation limit.
                group = "village"
            else:
                group = "attack"

            self._assign(environment, c, group_ids, group)
```