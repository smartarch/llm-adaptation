from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawned = 0
        self._farmer_spawned = False
        self._dispatch_cursor = 0

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

        # Feed villagers before they get close to the starvation threshold.
        # Warriors are fed at 4 steps because they also need time to travel.
        meal_candidates = sorted(
            (
                c for c in components
                if (
                    (self._role(c) == "warrior" and c.steps_since_meal >= 4)
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

        available = [c for c in components if id(c) not in assigned]
        farmers = [c for c in available if self._role(c) == "farmer"]

        # Spawn a farmer once, if the initial farmers and food supply allow it.
        # This provides more long-term food production.
        spawn_pair = None
        spawn_group = None
        if not self._farmer_spawned and len(farmers) >= 2 and wheat >= 10:
            spawn_pair = farmers[:2]
            spawn_group = "spawn farmer"

        # After the extra farmer is secured, spawn warriors from pairs of
        # farmers. Keep at least one farmer working, and avoid spending the
        # food reserve needed to feed the village.
        elif (
            self._farmer_spawned
            and self._warrior_spawned < 4
            and len(farmers) >= 3
            and wheat >= 20
        ):
            spawn_pair = farmers[:2]
            spawn_group = "spawn warrior"

        if spawn_pair is not None:
            for component in spawn_pair:
                self._assign(environment, component, spawn_group, group_ids)
                assigned.add(id(component))

            if spawn_group == "spawn farmer":
                self._farmer_spawned = True
            else:
                self._warrior_spawned += 1

        dragon_alive = environment.dragon.hp > 0

        # Stagger departures so the warriors are less likely to need meals
        # and return to the Village all at the same time.
        eligible_warriors = [
            c for c in components
            if (
                id(c) not in assigned
                and self._role(c) == "warrior"
                and c.steps_since_meal < 3
            )
        ]
        dispatched = None
        if dragon_alive and eligible_warriors:
            index = self._dispatch_cursor % len(eligible_warriors)
            dispatched = eligible_warriors[index]
            self._dispatch_cursor += 1

        for component in components:
            if id(component) in assigned:
                continue

            if not dragon_alive:
                group = "farm"
            elif self._role(component) == "farmer":
                group = "farm"
            elif component is dispatched:
                group = "cave"
            elif component.steps_since_meal >= 4:
                # If wheat was unavailable for a meal, keep the warrior in
                # the Village rather than sending a hungry warrior away.
                group = "farm"
            else:
                # Warriors waiting to be dispatched can remain in the Village
                # and contribute a little food.
                group = "farm"

            self._assign(environment, component, group, group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0

        for component in components:
            if not dragon_alive:
                group = "village"
            elif self._role(component) != "warrior":
                group = "village"
            elif component.steps_since_meal >= 4:
                # Return early enough to reach the Village and eat safely.
                group = "village"
            else:
                group = "attack"

            self._assign(environment, component, group, group_ids)