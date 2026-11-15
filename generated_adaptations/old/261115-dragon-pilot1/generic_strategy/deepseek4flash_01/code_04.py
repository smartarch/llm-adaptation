from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.any_warrior_seen = False

    def _assign(self, environment, component, decisions, group_id):
        decisions[id(component)] = group_id

    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        if warriors:
            self.any_warrior_seen = True

        # Meals are decided first so that spawning does not consume food
        # needed to keep villagers alive.
        eat_list = []
        for c in components:
            if c.role == "Warrior":
                # If a warrior is already in the village and somewhat hungry,
                # it is better to reset the hunger timer before another Cave trip.
                if c.steps_since_meal >= 3:
                    eat_list.append(c)
            else:
                if c.steps_since_meal >= 5:
                    eat_list.append(c)

        eat_list.sort(key=lambda c: c.steps_since_meal, reverse=True)
        for c in eat_list:
            if wheat > 0:
                self._assign(environment, c, decisions, "eat")
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
                self._assign(environment, c, decisions, target)
                available_farmers.remove(c)

            wheat -= cost
            if target == "spawn warrior":
                self.spawned_warriors += 1
                self.any_warrior_seen = True
            else:
                self.spawned_farmers += 1
            return True

        # Make sure an early warrior exists if we have not seen one yet.
        if not self.any_warrior_seen and self.spawned_warriors == 0:
            spawn_pair("spawn warrior")

        # Build a farming base. More farmers let us sustain warrior production.
        desired_farmers = 4
        if wheat >= 30 and step < 10:
            desired_farmers = 5

        spawned_farmers_this_step = 0
        while (
            len(farmers) + spawned_farmers_this_step < desired_farmers
            and len(available_farmers) >= 2
            and wheat >= 10
        ):
            if not spawn_pair("spawn farmer"):
                break
            spawned_farmers_this_step += 1

        # Spend remaining wheat on warriors.
        while len(available_farmers) >= 2 and wheat >= 12:
            if not spawn_pair("spawn warrior"):
                break

        # Warriors not eating go to the Cave if they can still attack
        # meaningfully. Very hungry warriors stay and farm so they can eat soon.
        for c in available_warriors:
            if c.steps_since_meal <= 2:
                self._assign(environment, c, decisions, "cave")
            else:
                self._assign(environment, c, decisions, "farm")

        # All remaining farmers work on the farm.
        for c in available_farmers:
            self._assign(environment, c, decisions, "farm")

        # Safety fallback: every villager must be assigned exactly once.
        for c in components:
            if id(c) not in decisions:
                if c.role == "Warrior":
                    self._assign(
                        environment,
                        c,
                        decisions,
                        "cave" if c.steps_since_meal <= 2 else "farm",
                    )
                else:
                    self._assign(environment, c, decisions, "farm")

        for c in components:
            environment.assign_group(c, decisions[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        decisions = {}

        warriors = [c for c in components if c.role == "Warrior"]
        for c in components:
            if c.role == "Warrior":
                self.any_warrior_seen = True
            else:
                self._assign(environment, c, decisions, "village")

        # Warriors at 6+ hunger cannot deal damage and must return.
        active = []
        for w in warriors:
            if w.steps_since_meal >= 6:
                self._assign(environment, w, decisions, "village")
            else:
                active.append(w)

        # Stagger rotations. If several warriors reach age 3 together, send
        # roughly half home now. The others keep attacking through age 5,
        # while the returning group eats and comes back as reinforcements.
        age3 = [w for w in active if w.steps_since_meal == 3]
        if len(age3) >= 2:
            age3.sort(key=lambda c: id(c))
            n_return = len(age3) // 2
            for w in age3[:n_return]:
                self._assign(environment, w, decisions, "village")

        remaining = [w for w in active if id(w) not in decisions]

        if remaining and all(w.steps_since_meal >= 5 for w in remaining):
            # All current Cave warriors are about to starve. Keep exactly one
            # attacker this step so the Dragon does not regenerate.
            keeper = min(
                remaining,
                key=lambda w: (w.steps_since_meal, id(w)),
            )
            for w in remaining:
                if w is keeper:
                    self._assign(environment, w, decisions, "attack")
                else:
                    self._assign(environment, w, decisions, "village")
        else:
            for w in remaining:
                if w.steps_since_meal >= 5:
                    self._assign(environment, w, decisions, "village")
                else:
                    self._assign(environment, w, decisions, "attack")

        # Safety: if nobody is attacking but somebody still can, keep one
        # warrior on the Dragon.
        has_attacker = any(
            decisions.get(id(w)) == "attack"
            for w in active
        )
        if not has_attacker and active:
            candidate = min(
                active,
                key=lambda w: (w.steps_since_meal, id(w)),
            )
            self._assign(environment, candidate, decisions, "attack")

        # Safety fallback for any unassigned component.
        for c in components:
            if id(c) not in decisions:
                self._assign(environment, c, decisions, "village")

        for c in components:
            environment.assign_group(c, decisions[id(c)])