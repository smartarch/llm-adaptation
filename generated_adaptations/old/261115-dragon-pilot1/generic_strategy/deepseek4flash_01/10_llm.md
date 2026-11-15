Strategy: rush the first warrior when none exists, otherwise quickly build up to six farmers and convert surplus wheat into warriors. Warriors attack through hunger level 5 and only return at 6, maximizing damage per Cave trip. Meal assignment is done before spawning so that food is not accidentally spent on new villagers while existing villagers are about to starve. Spawn loops preserve at least two farming villagers after the first warrior pair, keeping wheat income stable. Extra farmers are not sent to the Cave in the endgame, since their 1 damage is not worth the movement delay compared with the 3 damage warriors deal.

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

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if warriors:
            self.any_warrior_seen = True

        # Meals are assigned first. Warriors that have returned to the
        # village are prioritized, then farmers close to starvation.
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

        # First warrior as early as possible. If there is no warrior yet
        # and wheat is insufficient, spawn a farmer to build production.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
            elif wheat >= 10 and len(available_farmers) >= 2:
                spawn_pair("spawn farmer")
        else:
            # Build toward six farmers in the opening. Only one farmer pair
            # per step, so at least some villagers keep farming.
            if (
                step <= 5
                and len(farmers) < 6
                and len(available_farmers) >= 2
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

        # Spend remaining wheat on warriors. The first pair only needs two
        # available farmers; additional pairs require four so that at least
        # two farmers remain to produce wheat for the next step.
        spawned_warrior_pairs = 0
        while wheat >= 12 and len(available_farmers) >= 2:
            if spawned_warrior_pairs == 0:
                if not spawn_pair("spawn warrior"):
                    break
                spawned_warrior_pairs += 1
            else:
                if len(available_farmers) < 4:
                    break
                if not spawn_pair("spawn warrior"):
                    break
                spawned_warrior_pairs += 1

        # Warriors in the Village: those at hunger <= 3 can still make a
        # useful Cave trip. Hungrier warriors eat or recover first.
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
                # Farmers should normally not be in the Cave.
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
```