from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = [None] * len(villagers)
        wheat = max(0, environment.farm.wheat)
        warriors = list(environment.warriors)

        # Begin attacking earlier, while continuing to build reinforcements.
        launch = len(warriors) >= 3 or step >= 12

        # Feed villagers who must eat now, prioritizing the most overdue.
        urgent = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in urgent:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        if launch:
            # Refresh warriors before deployment so they have time to fight.
            for i, villager in enumerate(villagers):
                if (
                    assignments[i] is None
                    and villager.role == "Warrior"
                    and 2 <= villager.steps_since_meal < 5
                    and wheat >= 1
                ):
                    assignments[i] = "eat"
                    wheat -= 1

            for i, villager in enumerate(villagers):
                if (
                    assignments[i] is None
                    and villager.role == "Warrior"
                    and villager.steps_since_meal <= 2
                ):
                    assignments[i] = "cave"

        # Spawn warriors while they still have time to contribute.
        if step < 26:
            desired_warriors = 8
            needed = max(0, desired_warriors - len(warriors))
            reserve = min(4, len(villagers))
            affordable = max(0, int((wheat - reserve) // 12))

            candidates = [
                i
                for i, villager in enumerate(villagers)
                if assignments[i] is None and villager.steps_since_meal < 5
            ]
            candidates.sort(
                key=lambda i: (
                    villagers[i].role != "Warrior",
                    villagers[i].steps_since_meal,
                )
            )

            # Prefer to leave a farmer working when enough villagers remain.
            farmers = [
                i for i in candidates if villagers[i].role == "Farmer"
            ]
            if len(candidates) >= 3 and farmers:
                candidates.remove(farmers[-1])

            pairs = min(needed, affordable, len(candidates) // 2)
            for i in candidates[: 2 * pairs]:
                assignments[i] = "spawn warrior"

        for i, villager in enumerate(villagers):
            environment.assign_group(villager, assignments[i] or "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            # Travel now so the villager can eat before six missed meals.
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)