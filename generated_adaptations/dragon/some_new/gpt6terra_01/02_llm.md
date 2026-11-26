The strategy builds a warrior force while keeping villagers in the Village to farm and spawn reinforcements. Once enough warriors exist, it sends them to attack in waves. Cave villagers normally return when they have gone four steps without food, leaving time to travel and eat before six steps have passed. If the available cave force can finish the Dragon immediately, it attacks instead.

Food and spawning are budgeted against the currently observed wheat. Survival cannot be guaranteed if the initial resources are insufficient or the Dragon’s attacks are unfavorable.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = [None] * len(villagers)
        wheat = max(0, environment.farm.wheat)
        warriors = list(environment.warriors)

        # Start the assault once a useful force exists. If the deadline is
        # approaching, send whatever warriors remain.
        launch = len(warriors) >= 4 or step >= 12

        # Feed villagers who must eat now, prioritizing the most overdue.
        urgent = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in urgent:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        # Before deployment, refresh warriors who would otherwise have
        # little time to fight before needing to return.
        if launch:
            for i, v in enumerate(villagers):
                if (
                    assignments[i] is None
                    and v.role == "Warrior"
                    and 2 <= v.steps_since_meal < 5
                    and wheat >= 1
                ):
                    assignments[i] = "eat"
                    wheat -= 1

            for i, v in enumerate(villagers):
                if (
                    assignments[i] is None
                    and v.role == "Warrior"
                    and v.steps_since_meal <= 2
                ):
                    assignments[i] = "cave"

        # Spawn reinforcements while there is time for them to contribute.
        # Keep some wheat for upcoming meals, and preferably leave a farmer
        # working whenever there are at least three available villagers.
        if step < 26:
            desired_warriors = 8
            needed = max(0, desired_warriors - len(warriors))
            reserve = min(4, len(villagers))
            affordable = max(0, int((wheat - reserve) // 12))

            candidates = [
                i for i, v in enumerate(villagers)
                if assignments[i] is None and v.steps_since_meal < 5
            ]
            candidates.sort(
                key=lambda i: (
                    villagers[i].role != "Warrior",
                    villagers[i].steps_since_meal,
                )
            )

            farmers = [
                i for i in candidates if villagers[i].role == "Farmer"
            ]
            if len(candidates) >= 3 and farmers:
                candidates.remove(farmers[-1])

            pairs = min(needed, affordable, len(candidates) // 2)
            for i in candidates[: 2 * pairs]:
                assignments[i] = "spawn warrior"
            wheat -= 12 * pairs

        # Everyone not otherwise assigned works on the farm.
        for i, villager in enumerate(villagers):
            environment.assign_group(villager, assignments[i] or "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)

        # Villagers with fewer than five missed meals can potentially
        # contribute damage this step. Use even those due to return if
        # their combined attack can finish the Dragon immediately.
        finishing_damage = sum(
            3 if v.role == "Warrior" else 1
            for v in villagers
            if v.steps_since_meal < 5
        )
        can_finish = finishing_damage >= environment.dragon.hp

        for villager in villagers:
            if villager.steps_since_meal < 4:
                group = "attack"
            elif can_finish and villager.steps_since_meal < 5:
                group = "attack"
            else:
                group = "village"
            environment.assign_group(villager, group)
```