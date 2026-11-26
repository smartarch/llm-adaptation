from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._raid_started = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        wheat = max(0, environment.farm.wheat)

        raid_ready = (
            self._raid_started
            or environment.dragon.hp < 100
            or any(w.location == "Cave" for w in warriors)
            or len(warriors) >= 8
            or step >= 10
        )

        # Default to farming; every assignment is explicitly issued below.
        actions = ["farm"] * len(villagers)
        available = set(range(len(villagers)))

        # First feed those closest to starvation. Before a raid, also feed
        # warriors early enough to give them useful time at the cave.
        eat_candidates = [
            i for i, v in enumerate(villagers)
            if v.steps_since_meal >= 5
            or (
                raid_ready
                and v.role == "Warrior"
                and v.steps_since_meal >= 2
            )
        ]
        eat_candidates.sort(
            key=lambda i: villagers[i].steps_since_meal, reverse=True
        )
        for i in eat_candidates:
            if wheat >= 1:
                actions[i] = "eat"
                available.remove(i)
                wheat -= 1
            else:
                # Do not send an unfed villager away from the food supply.
                available.remove(i)

        # Keep some wheat for villagers likely to need meals next step.
        upcoming_meals = sum(
            1 for i, v in enumerate(villagers)
            if actions[i] != "eat" and v.steps_since_meal >= 4
        )
        upcoming_meals += sum(
            1 for v in warriors + farmers
            if v.location == "Cave" and v.steps_since_meal >= 3
        )
        spawn_budget = max(0, wheat - upcoming_meals)

        # Recruit while there is time to benefit. Leave one farmer working
        # when the population is large enough to do so.
        if step < 21 and environment.dragon.hp > 24:
            max_new = min(
                max(0, 12 - len(warriors)),
                int(spawn_budget // 12),
            )
            candidates = [
                i for i in available
                if villagers[i].steps_since_meal < 5
            ]

            farmer_candidates = [
                i for i in candidates if villagers[i].role == "Farmer"
            ]
            if len(candidates) >= 3 and farmer_candidates:
                # Preserve the best-fed farmer for production.
                keeper = min(
                    farmer_candidates,
                    key=lambda i: villagers[i].steps_since_meal,
                )
                candidates.remove(keeper)

            # During an active raid, keep at least five ready village
            # warriors available to depart rather than use them as parents.
            if raid_ready:
                ready_warriors = [
                    i for i in candidates
                    if villagers[i].role == "Warrior"
                    and villagers[i].steps_since_meal <= 1
                ]
                protected = set(ready_warriors[:5])
                candidates = [i for i in candidates if i not in protected]

            # Prefer farmers as parents so that warriors can fight.
            candidates.sort(
                key=lambda i: (
                    villagers[i].role != "Farmer",
                    -villagers[i].steps_since_meal,
                )
            )
            pairs = min(max_new, len(candidates) // 2)
            for i in candidates[: 2 * pairs]:
                actions[i] = "spawn warrior"
                available.remove(i)

        # Depart only when fed recently enough to attack and return before
        # reaching six consecutive steps without a meal.
        if raid_ready:
            for i in list(available):
                v = villagers[i]
                if v.role == "Warrior" and v.steps_since_meal <= 1:
                    actions[i] = "cave"
                    self._raid_started = True

        for villager, action in zip(villagers, actions):
            environment.assign_group(villager, action)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if villager.steps_since_meal >= 4:
                # Travel takes a step; eat on the following village step.
                action = "village"
            else:
                action = "attack"
                self._raid_started = True
            environment.assign_group(villager, action)