from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    @staticmethod
    def _group_id(group_ids, name):
        if name in group_ids:
            return name
        return group_ids[name]

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def _spawn_pair(self, components, assigned, keep_farmer=True):
        """Pick two fresh villagers, preferring not to use the last farmer."""
        candidates = [
            c for c in components
            if id(c) not in assigned and c.steps_since_meal <= 2
        ]
        candidates.sort(
            key=lambda c: (
                c.role != "Farmer",
                c.steps_since_meal,
                -c.hp,
            )
        )

        if len(candidates) < 2:
            return []

        if keep_farmer:
            farmers = [c for c in candidates if c.role == "Farmer"]
            # If more than two farmers are available, preserve one for farming.
            if len(farmers) > 2:
                candidates = [c for c in candidates if c is not farmers[-1]]

        return candidates[:2] if len(candidates) >= 2 else []

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()
        wheat = max(0, environment.farm.wheat)

        # Eat before villagers reach the starvation threshold. Warriors eat
        # earlier because they need to travel to the Cave before fighting.
        hungry = [
            c for c in components
            if c.steps_since_meal >= (3 if c.role == "Warrior" else 5)
        ]
        hungry.sort(key=lambda c: (c.steps_since_meal, -c.hp), reverse=True)

        for c in hungry:
            if wheat < 1:
                break
            self._assign(environment, c, self._group_id(group_ids, "eat"))
            assigned.add(id(c))
            wheat -= 1

        # Request warrior spawns whenever affordable. Further spawns beyond
        # the required two can provide enough combat strength to finish faster.
        # Do at most one spawn request per step to avoid stripping the farm.
        if wheat >= 12:
            pair = self._spawn_pair(components, assigned, keep_farmer=True)
            if pair:
                for c in pair:
                    self._assign(
                        environment, c, self._group_id(group_ids, "spawn warrior")
                    )
                    assigned.add(id(c))
                wheat -= 12
                self.spawned_warriors += 1

        # Ensure a farmer spawn is requested once the warrior requirement has
        # been met and sufficient wheat and villagers are available.
        elif (
            self.spawned_warriors >= 2
            and self.spawned_farmers < 1
            and wheat >= 10
        ):
            pair = self._spawn_pair(components, assigned, keep_farmer=True)
            if pair:
                for c in pair:
                    self._assign(
                        environment, c, self._group_id(group_ids, "spawn farmer")
                    )
                    assigned.add(id(c))
                self.spawned_farmers += 1

        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Farmer":
                self._assign(environment, c, self._group_id(group_ids, "farm"))
            elif c.steps_since_meal < 3:
                self._assign(environment, c, self._group_id(group_ids, "cave"))
            else:
                # If wheat was unavailable for a meal, keep the warrior in
                # the Village rather than sending a hungry warrior to fight.
                self._assign(environment, c, self._group_id(group_ids, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior":
                self._assign(environment, c, self._group_id(group_ids, "village"))
            elif c.steps_since_meal >= 4:
                # Return with enough time to reach the Village and eat.
                self._assign(environment, c, self._group_id(group_ids, "village"))
            else:
                self._assign(environment, c, self._group_id(group_ids, "attack"))