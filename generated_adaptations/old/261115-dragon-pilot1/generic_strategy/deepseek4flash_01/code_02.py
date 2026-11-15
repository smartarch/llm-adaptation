from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}

        def decide(component, group_id):
            decisions[id(component)] = group_id

        wheat = environment.farm.wheat

        # Reserve meals first. Warriors eat early enough to avoid a wasted
        # Cave trip; farmers can wait a little longer.
        eat_candidates = []
        for c in components:
            if c.role == "Warrior":
                hungry = c.steps_since_meal >= 2
            else:
                hungry = c.steps_since_meal >= 5

            if hungry:
                eat_candidates.append(c)

        eat_candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        for c in eat_candidates:
            if wheat > 0:
                decide(c, "eat")
                wheat -= 1

        # Warriors that are not eating either go to the Cave or, if no meal
        # was available for a hungry warrior, stay and farm so they can eat soon.
        for c in components:
            if id(c) in decisions:
                continue
            if c.role == "Warrior":
                if c.steps_since_meal <= 1:
                    decide(c, "cave")
                else:
                    decide(c, "farm")

        available_farmers = [
            c for c in components
            if c.role == "Farmer" and id(c) not in decisions
        ]

        spawn_group = None
        need_warrior = self.spawned_warriors < 2
        need_farmer = self.spawned_farmers < 2

        if len(available_farmers) >= 2:
            prefer_warrior = (
                need_warrior
                and (not need_farmer or self.spawned_warriors <= self.spawned_farmers)
            )

            if prefer_warrior and wheat >= 12:
                spawn_group = "spawn warrior"
            elif need_farmer and wheat >= 10:
                spawn_group = "spawn farmer"
            elif need_warrior and wheat >= 12:
                spawn_group = "spawn warrior"
            elif (
                step < 18
                and wheat >= 12
                and self.spawned_warriors < 4
                and len(available_farmers) >= 3
            ):
                # Add extra warriors only when there are still farmers left to
                # keep producing wheat.
                spawn_group = "spawn warrior"

        if spawn_group is not None:
            spawners = sorted(
                available_farmers,
                key=lambda c: c.steps_since_meal
            )[:2]

            for c in spawners:
                decide(c, spawn_group)

            if spawn_group == "spawn warrior":
                self.spawned_warriors += 1
                wheat -= 12
            else:
                self.spawned_farmers += 1
                wheat -= 10

        # All remaining farmers work on the farm.
        for c in available_farmers:
            if id(c) not in decisions:
                decide(c, "farm")

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                if c.role == "Warrior":
                    decide(c, "cave" if c.steps_since_meal <= 1 else "farm")
                else:
                    decide(c, "farm")

        for c in components:
            environment.assign_group(c, decisions[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        decisions = {}

        def decide(component, group_id):
            decisions[id(component)] = group_id

        warriors = []
        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                decide(c, "village")

        # Warriors that are too hungry to attack safely return to eat.
        for w in warriors:
            if w.steps_since_meal >= 4:
                decide(w, "village")

        active = [w for w in warriors if w.steps_since_meal <= 3]
        younger = [w for w in active if w.steps_since_meal < 3]
        at_three = [w for w in active if w.steps_since_meal == 3]

        # If everyone would reach the meal threshold at the same time, keep one
        # warrior attacking and rotate the rest home. This staggers meal breaks.
        if len(younger) == 0 and len(at_three) > 1:
            keeper = at_three[0]
            decide(keeper, "attack")
            for w in at_three[1:]:
                decide(w, "village")
        else:
            for w in active:
                decide(w, "attack")

        # If no warrior is attacking, try to keep at least one non-starving
        # warrior on the Dragon to limit regeneration.
        has_attacker = any(
            decisions.get(id(w)) == "attack"
            for w in warriors
        )

        if not has_attacker and warriors:
            candidate = min(warriors, key=lambda w: w.steps_since_meal)
            if candidate.steps_since_meal < 6:
                decide(candidate, "attack")

        # Safety fallback.
        for w in warriors:
            if id(w) not in decisions:
                decide(w, "village")

        for c in components:
            environment.assign_group(c, decisions[id(c)])