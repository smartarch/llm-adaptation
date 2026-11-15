Strategy: accelerate the opening by building a larger farming base (target 8 farmers in the first few steps when wheat allows) while still guaranteeing an early first warrior. After the first warrior exists, warrior spawning preserves at least three villagers on the farm whenever possible, so wheat income stays positive and the spawn loop can continue for many steps instead of collapsing after a single burst. Meals are reserved before spawning. Warriors attack through hunger level 5 and return at 6, maximizing damage per Cave trip. If wheat is too low to spawn a warrior early, farmers farm instead of spawning an extra farmer, preventing a wasted opening turn.

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

        # Guarantee an early warrior. If wheat is insufficient, farm instead
        # of spending the last wheat on another farmer, because farming this
        # step gets us to the first warrior sooner.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")

        # Farmer boom: build toward 8 farmers early when wheat allows.
        # One pair per step is enough and leaves other farmers producing.
        if self.any_warrior_seen or warriors:
            if (
                step <= 6
                and len(farmers) < 8
                and len(available_farmers) >= 2
                and wheat >= 20
            ):
                spawn_pair("spawn farmer")
            elif (
                step <= 4
                and len(farmers) < 8
                and len(available_farmers) >= 2
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

        # Warrior spawning. Once a warrior exists, try to leave at least
        # three farmers working so the economy remains sustainable.
        if len(farmers) >= 6:
            keep_farming = 3
        else:
            keep_farming = 2

        max_pairs = max(0, (len(available_farmers) - keep_farming) // 2)

        if not self.any_warrior_seen:
            max_pairs = max(max_pairs, 1 if len(available_farmers) >= 2 else 0)

        spawned_pairs = 0
        while spawned_pairs < max_pairs and wheat >= 12 and len(available_farmers) >= 2:
            if not spawn_pair("spawn warrior"):
                break
            spawned_pairs += 1

        # If wheat is still very high, spend surplus on additional farmers
        # early rather than letting it sit idle.
        if (
            step <= 7
            and len(farmers) < 8
            and wheat >= 30
            and len(available_farmers) >= 2
        ):
            spawn_pair("spawn farmer")

        # Warriors in the Village: those at hunger <= 3 can still make a
        # useful Cave trip; hungrier warriors eat/recover first.
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
```