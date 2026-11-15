Strategy: build the farming base to six farmers in the first few steps while keeping at least two farmers farming each turn, then convert wheat surplus into as many warriors as possible. Spawning is capped so that at least two farmers remain to produce food for the next step. Warriors attack through hunger level 5 and return at 6; village meals prioritize warriors that need to reset before another Cave trip. In the endgame, when the Dragon is low, remaining farmers are diverted to the Cave to add finishing damage instead of spawning more warriors.

```py
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
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if warriors:
            self.any_warrior_seen = True

        # Meals are assigned first so that spawning cannot consume food that
        # is needed to keep villagers from starving.
        def meal_priority(c):
            if c.role == "Warrior":
                if c.steps_since_meal >= 6:
                    return 100 + c.steps_since_meal
                if c.steps_since_meal >= 4:
                    return 60 + c.steps_since_meal
                if c.steps_since_meal >= 3:
                    return 30 + c.steps_since_meal
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

        finish_mode = dragon_hp <= 10 and step >= 9

        if not finish_mode:
            # Build toward six farmers early.  Only one new farmer pair is
            # spawned per step so the village keeps farming.
            if (
                step <= 3
                and len(farmers) < 6
                and len(available_farmers) >= 2
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

            # Spend the remaining wheat on warriors.  Leave at least two
            # farmers unassigned whenever possible so that next step still
            # has farm income for meals and future spawns.
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

        # Warriors in the Village either go to the Cave or recover / wait.
        for c in available_warriors:
            if c.steps_since_meal <= 3:
                decisions[id(c)] = "cave"
            else:
                decisions[id(c)] = "farm"

        # Endgame: send remaining farmers to the Cave to add finishing damage.
        if finish_mode:
            for c in available_farmers:
                if id(c) not in decisions:
                    decisions[id(c)] = "cave"
        else:
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
                # Farmers should not normally be in the Cave; send them back.
                decisions[id(c)] = "village"

        active = []
        for w in warriors:
            if w.steps_since_meal >= 6:
                decisions[id(w)] = "village"
            elif w.hp <= 1 and w.steps_since_meal >= 5:
                # Avoid losing a nearly-dead warrior to starvation.
                decisions[id(w)] = "village"
            else:
                active.append(w)

        # Attack through hunger level 5.  Returning at 6 gives the longest
        # safe attack window per Cave trip.
        for w in active:
            decisions[id(w)] = "attack"

        # If nobody is attacking but somebody still can, keep one attacker
        # on the Dragon to avoid regeneration.
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
```