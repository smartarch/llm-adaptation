from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._first_step = None
        self._attack_started = False

    def _age(self, step):
        if self._first_step is None:
            self._first_step = step
        return step - self._first_step

    def assign_in_village(self, components, environment, group_ids, step):
        villagers = list(components)
        age = self._age(step)
        actions = [None] * len(villagers)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = len(warriors) + len(farmers)
        wheat = max(0, int(environment.farm.wheat))

        # Feed overdue villagers first. Feed warriors early when they are
        # preparing to travel, so they can spend more time attacking.
        launch = self._attack_started or len(warriors) >= 5 or age >= 5
        meal_candidates = [
            i for i, v in enumerate(villagers)
            if v.steps_since_meal >= 5
            or (launch and v.role == "Warrior" and v.steps_since_meal >= 3)
        ]
        meal_candidates.sort(
            key=lambda i: (
                -villagers[i].steps_since_meal,
                villagers[i].hp,
            )
        )
        for i in meal_candidates:
            if wheat <= 0:
                break
            actions[i] = "eat"
            wheat -= 1

        # Keep someone in the Village to produce food where possible.
        village_farmers = sum(v.role == "Farmer" for v in villagers)
        reserve_warrior = None
        if village_farmers == 0 and age < 20:
            candidates = [
                i for i, v in enumerate(villagers)
                if v.role == "Warrior" and actions[i] is None
            ]
            if candidates:
                reserve_warrior = max(
                    candidates, key=lambda i: villagers[i].steps_since_meal
                )

        if launch:
            for i, v in enumerate(villagers):
                if (
                    actions[i] is None
                    and v.role == "Warrior"
                    and v.steps_since_meal <= 2
                    and i != reserve_warrior
                ):
                    actions[i] = "cave"

        # Late in the game, use farmers as reinforcements too, while
        # normally leaving one person behind to farm.
        if age >= 20:
            candidates = [
                i for i, v in enumerate(villagers)
                if actions[i] is None
                and v.role == "Farmer"
                and v.steps_since_meal <= 2
            ]
            already_staying = any(
                actions[i] == "eat"
                or (actions[i] is None and i not in candidates)
                for i in range(len(villagers))
            )
            keep = 0 if already_staying or age >= 26 else 1
            for i in candidates[:max(0, len(candidates) - keep)]:
                actions[i] = "cave"

        # Spawn only with wheat on hand, preserving a modest food reserve.
        # Prefer building a farming base early, then recruit warriors.
        food_reserve = 2 + (population + 3) // 4
        available_for_spawning = max(0, wheat - food_reserve)
        projected_farmers = len(farmers)
        projected_warriors = len(warriors)

        for _ in range(2):
            if age > 12:
                break

            free = [i for i, action in enumerate(actions) if action is None]
            if len(free) < 2:
                break

            if projected_farmers < 2 and age <= 7:
                group, cost = "spawn farmer", 10
            elif projected_warriors < 7:
                group, cost = "spawn warrior", 12
            else:
                break

            if available_for_spawning < cost:
                break

            # Use warriors as parents first, leaving farmers to produce wheat.
            free.sort(key=lambda i: villagers[i].role != "Warrior")
            for i in free[:2]:
                actions[i] = group
            available_for_spawning -= cost
            if group == "spawn farmer":
                projected_farmers += 1
            else:
                projected_warriors += 1

        for i, villager in enumerate(villagers):
            environment.assign_group(villager, actions[i] or "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        villagers = list(components)
        age = self._age(step)

        # At four steps since a meal, travel back now: after the move,
        # the villager can eat in the Village before reaching six.
        eligible = [v for v in villagers if v.steps_since_meal < 4]
        damage = sum(3 if v.role == "Warrior" else 1 for v in eligible)

        # Briefly gather an initial wave, but do not wait indefinitely.
        attack = (
            self._attack_started
            or damage >= 6
            or (damage > 0 and damage >= environment.dragon.hp)
            or age >= 9
        )

        for villager in villagers:
            if villager.steps_since_meal >= 4:
                group = "village"
            elif attack:
                group = "attack"
                self._attack_started = True
            else:
                group = "cave"
            environment.assign_group(villager, group)