from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    @staticmethod
    def _group(group_ids, name):
        if name in group_ids:
            return name
        # Also tolerate a mapping of group names to IDs.
        return group_ids[name]

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = max(0, environment.farm.wheat)
        assigned = set()

        # Feed before starvation. Warriors are fed earlier so they can travel
        # to the Cave and fight while still healthy.
        hungry = [
            c for c in components
            if c.steps_since_meal >= (
                3 if c.role == "Warrior" else 5
            )
        ]
        hungry.sort(key=lambda c: (c.steps_since_meal, -c.hp), reverse=True)

        for c in hungry:
            if wheat < 1:
                break
            self._assign(environment, c, self._group(group_ids, "eat"))
            assigned.add(id(c))
            wheat -= 1

        # Prefer farmers as the spawn pair, preserving warriors for combat.
        def fresh_unassigned():
            return [
                c for c in components
                if id(c) not in assigned and c.steps_since_meal <= 2
            ]

        def choose_pair():
            candidates = fresh_unassigned()
            candidates.sort(
                key=lambda c: (
                    c.role != "Farmer",
                    c.steps_since_meal,
                    -c.hp,
                )
            )
            return candidates[:2] if len(candidates) >= 2 else []

        # Request two warrior spawns as soon as the cost and a pair are available.
        while self.spawned_warriors < 2 and wheat >= 12:
            pair = choose_pair()
            if not pair:
                break
            for c in pair:
                self._assign(
                    environment, c, self._group(group_ids, "spawn warrior")
                )
                assigned.add(id(c))
            wheat -= 12
            self.spawned_warriors += 1

        # Also request a farmer spawn once the warrior requests have been made.
        if self.spawned_warriors >= 2 and self.spawned_farmers < 1 and wheat >= 10:
            pair = choose_pair()
            if pair:
                for c in pair:
                    self._assign(
                        environment, c, self._group(group_ids, "spawn farmer")
                    )
                    assigned.add(id(c))
                wheat -= 10
                self.spawned_farmers += 1

        # Farmers remain in the Village. Healthy warriors head to the Cave;
        # warriors who need food stay to farm if no wheat was available to eat.
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Farmer":
                self._assign(environment, c, self._group(group_ids, "farm"))
            elif c.steps_since_meal < 3:
                self._assign(environment, c, self._group(group_ids, "cave"))
            else:
                self._assign(environment, c, self._group(group_ids, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        components = list(components)

        # Stagger returns: sending every hungry warrior back at once can leave
        # the Dragon unattended and allow it to regenerate. Return the hungriest
        # warrior, while the others keep attacking; return additional warriors
        # on later steps if they also need to eat.
        warriors = [c for c in components if c.role == "Warrior"]
        returning = None
        eligible = [c for c in warriors if c.steps_since_meal >= 4]
        if eligible:
            eligible.sort(
                key=lambda c: (c.steps_since_meal, -c.hp),
                reverse=True,
            )
            returning = eligible[0]

        for c in components:
            if c.role != "Warrior":
                self._assign(environment, c, self._group(group_ids, "village"))
            elif c is returning:
                self._assign(environment, c, self._group(group_ids, "village"))
            else:
                self._assign(environment, c, self._group(group_ids, "attack"))