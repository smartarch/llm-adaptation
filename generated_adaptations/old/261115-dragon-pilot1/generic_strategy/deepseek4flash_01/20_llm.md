Strategy: keep the proven six-farmer economy and hunger-5 attack window, but remove two sources of lost time. First, do not spend opening wheat on an extra farmer before the first warrior can be spawned; farming with the existing villagers reaches the first warrior sooner. Second, send the first warrior to the Cave immediately and start attacking as soon as any healthy warrior is there, instead of waiting for a second warrior. The starving-warrior “blocker” remains in place in the Cave to prevent regeneration during rotation gaps. The endgame farmer rush is removed because it was slower in simulation.

```py
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

        # Meals are decided before spawning so food is not spent on new
        # villagers while someone is about to starve.
        def meal_priority(c):
            if c.steps_since_meal >= 6:
                return 200 + c.steps_since_meal
            if c.role == "Warrior":
                if c.steps_since_meal >= 4:
                    return 80 + c.steps_since_meal
            else:
                if c.steps_since_meal >= 5:
                    return 60 + c.steps_since_meal
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

        # First warrior as early as possible. If there is not enough wheat,
        # farm with the existing villagers instead of spawning another farmer,
        # because that reaches the first warrior sooner.
        if not self.any_warrior_seen and not warriors:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
        else:
            # Build toward six farmers during the opening, but only one farmer
            # pair per step so the rest of the village keeps producing wheat.
            if (
                step <= 4
                and len(farmers) < 6
                and len(available_farmers) >= 2
                and wheat >= 10
            ):
                spawn_pair("spawn farmer")

        # Spend remaining wheat on warriors. The first pair is always allowed;
        # additional pairs preserve at least two working farmers when possible.
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

        # Send warriors to the Cave eagerly. If attacks have not started yet,
        # a warrior with up to 3 hunger steps can still make a useful trip.
        if not self.started_attack:
            hunger_limit = 3
        else:
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
                    decisions[id(c)] = (
                        "cave" if c.steps_since_meal <= hunger_limit else "farm"
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
            if w.steps_since_meal >= 6:
                decisions[id(w)] = "village"
            elif w.hp <= 1 and w.steps_since_meal >= 5:
                decisions[id(w)] = "village"
            else:
                active.append(w)

        if not active:
            # No warrior can deal damage. Keep one warrior attacking anyway
            # as a regeneration blocker when attacks have already started.
            if self.started_attack and warriors:
                candidates = [w for w in warriors if w.hp > 0]
                if not candidates:
                    candidates = warriors

                blocker = min(
                    candidates,
                    key=lambda w: (w.steps_since_meal, -w.hp, id(w)),
                )
                decisions[id(blocker)] = "attack"

            for w in warriors:
                if id(w) not in decisions:
                    decisions[id(w)] = "village"
        else:
            # Attack immediately with every warrior that can still deal damage.
            for w in active:
                decisions[id(w)] = "attack"

            for w in warriors:
                if id(w) not in decisions:
                    decisions[id(w)] = "village"

            self.started_attack = True

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
```