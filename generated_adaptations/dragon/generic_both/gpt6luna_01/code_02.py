from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_farmer = False
        self._spawned_warriors = 0

    @staticmethod
    def _group_id(group_ids, name):
        for group_id in group_ids:
            if group_id == name or str(group_id) == name:
                return group_id
        return name

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    def _assign(self, environment, component, group_ids, name):
        environment.assign_group(component, self._group_id(group_ids, name))

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        assignments = {}

        farmers = [c for c in components if self._role(c) == "farmer"]
        warriors = [c for c in components if self._role(c) == "warrior"]

        # Feed warriors before they return to the Cave, and feed villagers
        # whose meal timers are close to the starvation threshold.
        urgent = []
        for c in warriors:
            if getattr(c, "steps_since_meal", 0) >= 3:
                urgent.append(c)
        for c in farmers:
            if getattr(c, "steps_since_meal", 0) >= 5:
                urgent.append(c)

        urgent.sort(key=lambda c: getattr(c, "steps_since_meal", 0), reverse=True)
        for c in urgent:
            if wheat > 0:
                assignments[c] = "eat"
                wheat -= 1

        # Farmers can eat at age 4 when food is available, avoiding a
        # last-minute meal while preserving food for more urgent villagers.
        for c in sorted(
            farmers,
            key=lambda x: getattr(x, "steps_since_meal", 0),
            reverse=True,
        ):
            if c not in assignments and getattr(c, "steps_since_meal", 0) >= 4 and wheat > 0:
                assignments[c] = "eat"
                wheat -= 1

        # Spawn in stages. Two villagers must be assigned to a spawn group;
        # retain a small reserve for meals before spending wheat.
        spawn_target = None
        spawn_cost = 0
        if not self._spawned_farmer:
            spawn_target, spawn_cost = "spawn farmer", 10
        elif self._spawned_warriors < 2:
            spawn_target, spawn_cost = "spawn warrior", 12

        if spawn_target is not None:
            reserve = min(4, max(2, sum(
                1 for c in components
                if getattr(c, "steps_since_meal", 0) >= 3
            )))
            providers = [
                c for c in components
                if c not in assignments
                and getattr(c, "steps_since_meal", 0) < 4
            ]
            if len(providers) >= 2 and wheat >= spawn_cost + reserve:
                for c in providers[:2]:
                    assignments[c] = spawn_target
                if spawn_target == "spawn farmer":
                    self._spawned_farmer = True
                else:
                    self._spawned_warriors += 1

        for c in components:
            if c in assignments:
                group = assignments[c]
            elif self._role(c) == "warrior":
                # If a meal is due but no wheat is currently available, stay
                # in the Village rather than making a hungry trip to the Cave.
                group = (
                    "farm"
                    if getattr(c, "steps_since_meal", 0) >= 3
                    else "cave"
                )
            else:
                group = "farm"
            self._assign(environment, c, group_ids, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if self._role(c) != "warrior":
                group = "village"
            elif getattr(c, "steps_since_meal", 0) >= 4:
                group = "village"
            else:
                group = "attack"
            self._assign(environment, c, group_ids, group)