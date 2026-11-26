from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._phase = "build"

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = [None] * len(villagers)
        wheat = max(0, environment.farm.wheat)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = warriors + farmers

        # Pay for urgent meals first, before committing wheat to spawning.
        urgent = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 4),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in urgent:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        # Start the assault with a large, freshly fed group. The deadline
        # prevents excessive buildup when recruitment is slow.
        if self._phase == "build":
            enough_force = len(warriors) >= 13
            time_to_launch = step >= 15 and len(warriors) >= 6
            village_warriors = [
                i for i, v in enumerate(villagers)
                if v.role == "Warrior"
            ]
            meals_needed = sum(
                assignments[i] != "eat" for i in village_warriors
            )
            if (
                (enough_force or time_to_launch)
                and village_warriors
                and wheat >= meals_needed
            ):
                for i in village_warriors:
                    if assignments[i] is None:
                        assignments[i] = "eat"
                        wheat -= 1
                self._phase = "attack"

                # This turn is for preparation; departure is next turn.
                for i in range(len(villagers)):
                    if assignments[i] is None:
                        assignments[i] = "farm"
                for villager, group in zip(villagers, assignments):
                    environment.assign_group(villager, group)
                return

        if self._phase == "attack":
            # Returning warriors eat as soon as possible, then depart
            # with enough time for multiple attacks.
            for i, v in enumerate(villagers):
                if (
                    assignments[i] is None
                    and v.role == "Warrior"
                    and v.steps_since_meal >= 2
                    and wheat >= 1
                ):
                    assignments[i] = "eat"
                    wheat -= 1

            for i, v in enumerate(villagers):
                if assignments[i] is not None:
                    continue
                if v.role == "Warrior" and v.steps_since_meal <= 1:
                    assignments[i] = "cave"
                else:
                    assignments[i] = "farm"

        else:
            # Keep enough wheat for imminent meals, including any villagers
            # who happen to be returning from the Cave.
            reserve = 3
            reserve += sum(
                1 for i, v in enumerate(villagers)
                if assignments[i] is None and v.steps_since_meal >= 3
            )
            reserve += sum(
                1 for v in population
                if v.location == "Cave" and v.steps_since_meal >= 3
            )

            available = [
                i for i in range(len(villagers))
                if assignments[i] is None
            ]

            # Protect up to two farmers for production, but leave at
            # least two villagers available as potential spawn parents.
            farmer_indices = sorted(
                (i for i in available if villagers[i].role == "Farmer"),
                key=lambda i: villagers[i].steps_since_meal,
            )
            protect_count = min(2, len(farmer_indices), max(0, len(available) - 2))
            protected = set(farmer_indices[:protect_count])

            candidates = [i for i in available if i not in protected]
            candidates.sort(
                key=lambda i: (
                    villagers[i].role != "Warrior",
                    -villagers[i].steps_since_meal,
                )
            )

            # If the economy has no farmers, create one first.
            if not farmers and len(candidates) >= 2 and wheat - reserve >= 10:
                for i in candidates[:2]:
                    assignments[i] = "spawn farmer"
                wheat -= 10
                candidates = candidates[2:]

            affordable = max(0, int((wheat - reserve) // 12))
            desired = max(0, 13 - len(warriors))
            pairs = min(affordable, desired, len(candidates) // 2)
            for i in candidates[:2 * pairs]:
                assignments[i] = "spawn warrior"
            wheat -= 12 * pairs

            for i in range(len(villagers)):
                if assignments[i] is None:
                    assignments[i] = "farm"

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            # Returning takes one step; do not make a lethal-attack
            # exception to the meal deadline.
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)