from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.any_warrior_seen = False

    # ------------------------------------------------------------------
    # Village
    # ------------------------------------------------------------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if warriors:
            self.any_warrior_seen = True

        # Meals first: starvation protection has priority over spawning.
        def meal_priority(c):
            if c.role == "Warrior":
                if c.steps_since_meal >= 6:
                    return 120 + c.steps_since_meal
                if c.steps_since_meal >= 4:
                    return 70 + c.steps_since_meal
            else:
                if c.steps_since_meal >= 5:
                    return 50 + c.steps_since_meal
            return 0

        meal_candidates = sorted(
            components,
            key=lambda c: (meal_priority(c), c.steps_since_meal),
            reverse=True,
        )

        for c in meal_candidates:
            if wheat <= 0:
                break
            if meal_priority(c) > 0:
                decisions[id(c)] = "eat"
                wheat -= 1

        available_farmers = [c for c in farmers if id(c) not in decisions]
        available_warriors = [c for c in warriors if id(c) not in decisions]

        def spawn_pair(target):
            nonlocal wheat
            if len(available_farmers) < 2:
                return False

            cost = 12 if target == "spawn warrior" else 10
            if wheat < cost:
                return False

            available_farmers.sort(key=lambda c: c.steps_since_meal)
            pair = available_farmers[:2]
            for c in pair:
                available_farmers.remove(c)
                decisions[id(c)] = target

            wheat -= cost

            if target == "spawn warrior":
                self.any_warrior_seen = True
            return True

        # First warrior as early as possible. Do not spend the opening
        # wheat on extra farmers before a warrior exists.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
        else:
            # Grow the farming base only while wheat is comfortably above
            # the first-warrior threshold. Target five farmers, which is
            # enough income without delaying warrior production too much.
            if (
                step <= 4
                and len(farmers) < 5
                and len(available_farmers) >= 2
                and wheat >= 18
            ):
                spawn_pair("spawn farmer")
            elif (
                step <= 6
                and len(farmers) < 6
                and len(available_farmers) >= 2
                and wheat >= 30
            ):
                spawn_pair("spawn farmer")

        # Convert remaining wheat into warriors. Keep exactly two farmers
        # working when possible so next step still has farm income.
        max_pairs = max(0, (len(available_farmers) - 2) // 2)
        if not self.any_warrior_seen:
            max_pairs = max(max_pairs, 1 if len(available_farmers) >= 2 else 0)

        spawned_pairs = 0
        while (
            spawned_pairs < max_pairs
            and wheat >= 12
            and len(available_farmers) >= 2
        ):
            if not spawn_pair("spawn warrior"):
                break
            spawned_pairs += 1

        # Warriors in the Village: at hunger <= 3 they can still reach the
        # Cave and attack usefully before needing a meal. Hungrier warriors
        # wait and farm so they can eat soon.
        for c in available_warriors:
            if c.steps_since_meal <= 3:
                decisions[id(c)] = "cave"
            else:
                decisions[id(c)] = "farm"

        # Remaining farmers farm.
        for c in available_farmers:
            if id(c) not in decisions:
                decisions[id(c)] = "farm"

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                if c.role == "Warrior":
                    decisions[id(c)] = (
                        "cave" if c.steps_since_meal <= 3 else "farm"
                    )
                else:
                    decisions[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, decisions[id(c)])

    # ------------------------------------------------------------------
    # Cave
    # ------------------------------------------------------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        decisions = {}

        warriors = [c for c in components if c.role == "Warrior"]

        for c in components:
            if c.role == "Warrior":
                self.any_warrior_seen = True
            else:
                decisions[id(c)] = "village"

        active = []
        for w in warriors:
            # At hunger 6 the warrior cannot deal damage anyway.
            if w.steps_since_meal >= 6:
                decisions[id(w)] = "village"
            # Very low HP warriors return before starvation can kill them.
            elif w.hp <= 1 and w.steps_since_meal >= 5:
                decisions[id(w)] = "village"
            else:
                active.append(w)

        # Attack through hunger level 5 to maximize damage per Cave trip.
        for w in active:
            decisions[id(w)] = "attack"

        # If nobody is attacking but a warrior still can, keep one attacker
        # on the Dragon so it does not regenerate.
        has_attacker = any(
            decisions.get(id(w)) == "attack" for w in active
        )
        if not has_attacker and active:
            candidate = min(
                active,
                key=lambda w: (w.steps_since_meal, -w.hp, id(w)),
            )
            decisions[id(candidate)] = "attack"

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                decisions[id(c)] = "village"

        for c in components:
            environment.assign_group(c, decisions[id(c)])