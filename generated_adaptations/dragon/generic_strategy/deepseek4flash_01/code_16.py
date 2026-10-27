from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.any_warrior_seen = False
        self.started_attack = False
        self.last_attackers = 0
        self.cave_warriors = 0

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

        # Meals are decided before spawning so that food is not spent on new
        # villagers while an existing villager is about to starve.
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

        # First warrior as early as possible. If that is not possible yet,
        # a farmer may be spawned to build wheat production.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
            elif wheat >= 10 and len(available_farmers) >= 2:
                spawn_pair("spawn farmer")
        else:
            # Build a sustainable farming base early.
            if (
                step <= 3
                and len(farmers) < 6
                and len(available_farmers) >= 2
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

        # Convert surplus wheat into warriors. One pair per step is always
        # allowed; extra pairs preserve two working farmers when possible.
        if len(available_farmers) >= 2:
            max_pairs = max(1, (len(available_farmers) - 2) // 2)
            spawned_pairs = 0
            while (
                spawned_pairs < max_pairs
                and wheat >= 12
                and len(available_farmers) >= 2
            ):
                if not spawn_pair("spawn warrior"):
                    break
                spawned_pairs += 1

        # Warrior movement to the Cave.
        if not self.started_attack:
            # Do not send a lone warrior to wait hungrily in the Cave.
            # Hold warriors in the Village until at least two can travel.
            fresh = [
                c for c in available_warriors
                if c.steps_since_meal <= 3
            ]

            if self.cave_warriors >= 1:
                for c in available_warriors:
                    if c.steps_since_meal <= 3:
                        decisions[id(c)] = "cave"
                    else:
                        decisions[id(c)] = "farm"
            elif len(fresh) >= 2:
                for c in fresh:
                    decisions[id(c)] = "cave"
                for c in available_warriors:
                    if id(c) not in decisions:
                        decisions[id(c)] = "farm"
            else:
                for c in available_warriors:
                    decisions[id(c)] = "farm"
        else:
            # Once attacks have started, keep coverage if the previous step
            # had no attacker by allowing one extra hunger tick.
            hunger_limit = 4 if self.last_attackers == 0 else 3
            for c in available_warriors:
                if c.steps_since_meal <= hunger_limit:
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
                    if not self.started_attack:
                        decisions[id(c)] = "farm"
                    else:
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

        active = [
            w for w in warriors
            if w.steps_since_meal < 6
        ]
        starving = [
            w for w in warriors
            if w.steps_since_meal >= 6
        ]

        if not self.started_attack:
            # Wait for a pair, or start anyway if waiting would starve the
            # only available warrior or if time is getting short.
            can_start = False
            if len(active) >= 2:
                can_start = True
            elif step >= 10 and active:
                can_start = True
            elif step >= 6 and any(w.steps_since_meal >= 5 for w in active):
                can_start = True

            if can_start:
                for w in active:
                    decisions[id(w)] = "attack"
                for w in starving:
                    decisions[id(w)] = "village"
                self.started_attack = True
            else:
                for w in active:
                    decisions[id(w)] = "cave"
                for w in starving:
                    decisions[id(w)] = "village"
        else:
            if active:
                # Attack with every warrior that can still deal damage.
                for w in active:
                    decisions[id(w)] = "attack"
                for w in starving:
                    decisions[id(w)] = "village"
            else:
                # No warrior can deal damage. Keep one starving warrior on
                # attack anyway, because an attack — even for 0 damage —
                # prevents the Dragon from regenerating this step.
                candidates = [w for w in warriors if w.hp > 1]
                if not candidates:
                    candidates = warriors

                if candidates:
                    blocker = min(
                        candidates,
                        key=lambda w: (w.steps_since_meal, -w.hp, id(w)),
                    )
                    decisions[id(blocker)] = "attack"

                for w in warriors:
                    if id(w) not in decisions:
                        decisions[id(w)] = "village"

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                decisions[id(c)] = "village"

        self.last_attackers = sum(
            1 for c in components
            if decisions[id(c)] == "attack"
        )
        self.cave_warriors = sum(
            1 for c in components
            if c.role == "Warrior" and decisions[id(c)] != "village"
        )

        for c in components:
            environment.assign_group(c, decisions[id(c)])