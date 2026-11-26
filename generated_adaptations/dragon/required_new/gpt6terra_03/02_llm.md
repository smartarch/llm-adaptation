The strategy builds a warrior force while keeping a farmer working when possible. Warriors leave only when fed enough to attack and return before their meal deadline; cave villagers return when their meal counter reaches 4. Food for imminent meals is reserved before spawning.

The six-step meal requirement cannot be guaranteed from every possible starting state—for example, if wheat is unavailable when a villager must eat. The strategy prioritizes those meals and farms when necessary.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = [None] * len(villagers)
        wheat = max(0, environment.farm.wheat)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        all_villagers = warriors + farmers

        # First feed those who cannot safely skip another meal.
        due = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in due:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        # Feed prospective attackers early enough to make a useful cave trip.
        final_push = step >= 24
        prospective_attackers = sorted(
            (
                i for i, v in enumerate(villagers)
                if assignments[i] is None
                and 3 <= v.steps_since_meal < 5
                and (v.role == "Warrior" or final_push)
            ),
            key=lambda i: -villagers[i].steps_since_meal,
        )
        for i in prospective_attackers:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        # Reserve food for villagers likely to need it on the next step,
        # including those returning from the cave.
        reserve = 2
        reserve += sum(
            1 for i, v in enumerate(villagers)
            if assignments[i] is None and v.steps_since_meal >= 4
        )
        reserve += sum(
            1 for v in all_villagers
            if v.location == "Cave" and v.steps_since_meal >= 4
        )

        available = [
            i for i in range(len(villagers))
            if assignments[i] is None
        ]

        # Produce warriors early, but stop once the force is large enough
        # or there is too little time for a new warrior to contribute.
        target_warriors = 8
        remaining_to_spawn = max(0, target_warriors - len(warriors))
        if step < 17 and remaining_to_spawn and len(available) >= 2:
            # Keep one farmer farming when there are enough villagers to
            # both farm and spawn in this step.
            protected_farmer = None
            if len(available) >= 3:
                protected_farmer = next(
                    (i for i in available if villagers[i].role == "Farmer"),
                    None,
                )

            spawn_candidates = [
                i for i in available if i != protected_farmer
            ]
            # Prefer using extra farmers, leaving warriors free to fight.
            spawn_candidates.sort(
                key=lambda i: (
                    villagers[i].role != "Farmer",
                    villagers[i].steps_since_meal,
                )
            )

            affordable = max(0, int((wheat - reserve) // 12))
            pairs = min(
                remaining_to_spawn,
                affordable,
                len(spawn_candidates) // 2,
            )
            for i in spawn_candidates[: 2 * pairs]:
                assignments[i] = "spawn warrior"
            wheat -= 12 * pairs

        # A departure at meal counter 2 permits an attack, then a return
        # to the village for a meal before the six-step limit.
        for i, villager in enumerate(villagers):
            if assignments[i] is not None:
                continue

            ready = villager.steps_since_meal <= 2
            if ready and (villager.role == "Warrior" or final_push):
                assignments[i] = "cave"
            else:
                assignments[i] = "farm"

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)

        # If this turn can end the game, also use villagers who would
        # otherwise need to return immediately.
        possible_damage = sum(
            3 if v.role == "Warrior" else 1
            for v in villagers
            if v.steps_since_meal <= 4
        )
        lethal = possible_damage >= environment.dragon.hp

        for villager in villagers:
            if villager.steps_since_meal <= 3:
                group = "attack"
            elif lethal and villager.steps_since_meal == 4:
                group = "attack"
            else:
                group = "village"
            environment.assign_group(villager, group)
```