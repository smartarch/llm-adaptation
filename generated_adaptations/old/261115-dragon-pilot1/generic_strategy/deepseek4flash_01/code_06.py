from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
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

        # Meals first.  Warriors close to starvation are highest priority,
        # then farmers close to starvation, then other hungry warriors.
        def meal_urgency(c):
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
            key=lambda c: (meal_urgency(c), c.steps_since_meal),
            reverse=True,
        )

        for c in meal_candidates:
            if wheat <= 0:
                break
            if meal_urgency(c) > 0:
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
                self.spawned_warriors += 1
                self.any_warrior_seen = True
            else:
                self.spawned_farmers += 1
            return True

        # Get the first warrior as soon as possible.  If there is not enough
        # wheat for a warrior yet, spawn a farmer to improve future income.
        if self.spawned_warriors == 0 and not self.any_warrior_seen:
            if wheat >= 12 and len(available_farmers) >= 2:
                spawn_pair("spawn warrior")
            elif wheat >= 10 and len(available_farmers) >= 2 and len(farmers) < 4:
                spawn_pair("spawn farmer")
        else:
            # Build the farming base.  The early fifth farmer is deliberately
            # allowed when wheat is high: it enables double-warrior spawns.
            if len(available_farmers) >= 2 and wheat >= 10:
                if len(farmers) < 4:
                    spawn_pair("spawn farmer")
                elif (
                    len(farmers) == 4
                    and step <= 9
                    and wheat >= 18
                ):
                    spawn_pair("spawn farmer")
                elif (
                    len(farmers) == 4
                    and step <= 12
                    and self.spawned_warriors >= 4
                    and wheat < 24
                ):
                    spawn_pair("spawn farmer")

        # Spend remaining wheat on warriors.  This loop allows multiple
        # warrior pairs to be spawned in the same step when enough farmers
        # and wheat are available.
        while len(available_farmers) >= 2 and wheat >= 12:
            if not spawn_pair("spawn warrior"):
                break

        # Healthy / freshly-fed warriors go toward the Cave.  Warriors who
        # missed a meal and are still in the Village farm while waiting.
        for c in available_warriors:
            if c.steps_since_meal <= 2:
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
                        "cave" if c.steps_since_meal <= 2 else "farm"
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
                # Farmers should not be in the Cave.
                decisions[id(c)] = "village"

        # Warriors at hunger 6+ cannot damage.  Low-HP warriors at hunger 5
        # are also sent home to avoid starving to death.
        active = []
        for w in warriors:
            if w.steps_since_meal >= 6:
                decisions[id(w)] = "village"
            elif w.hp <= 1 and w.steps_since_meal >= 5:
                decisions[id(w)] = "village"
            else:
                active.append(w)

        # Attack through hunger level 5.  Returning at level 6 gives a longer
        # attack window per warrior than returning earlier.
        for w in active:
            decisions[id(w)] = "attack"

        # Safety: if nobody is attacking but a warrior is still capable,
        # keep at least one attacker in the Cave.
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