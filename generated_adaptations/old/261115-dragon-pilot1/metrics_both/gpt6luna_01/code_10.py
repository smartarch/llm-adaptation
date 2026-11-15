from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {"spawn warrior": 0, "spawn farmer": 0}

    @staticmethod
    def _role(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, environment.farm.wheat)
        assigned = set()
        farmers = []

        # Feed Warriors before they leave. If wheat is temporarily unavailable,
        # keep them in the Village eating rather than sending them out hungry.
        for c in components:
            if self._role(c) == "warrior":
                if c.steps_since_meal > 0:
                    self._assign(environment, c, "eat")
                    assigned.add(id(c))
                    if wheat > 0:
                        wheat -= 1
            else:
                farmers.append(c)

        # Farmers must eat before their sixth consecutive step without food.
        for c in farmers:
            if c.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, c, "eat")
                assigned.add(id(c))
                wheat -= 1

        # Keep wheat aside for Farmers nearing their meal deadline.
        reserve = sum(
            1 for c in farmers
            if id(c) not in assigned and c.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - reserve)

        candidates = [
            c for c in farmers
            if id(c) not in assigned and c.steps_since_meal < 4
        ]
        candidates.sort(key=lambda c: (c.steps_since_meal, -c.hp))

        # Use pairs to spawn, while retaining at least two Farmers to work.
        # Warriors are prioritized because they directly increase Dragon damage.
        while len(candidates) >= 4:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if not outstanding:
                break

            name = min(
                outstanding,
                key=lambda n: (
                    self._spawned[n],
                    0 if n == "spawn warrior" else 1,
                ),
            )
            cost = 12 if name == "spawn warrior" else 10
            if spawn_wheat < cost:
                break

            pair = candidates[:2]
            candidates = candidates[2:]
            for c in pair:
                self._assign(environment, c, name)
                assigned.add(id(c))

            self._spawned[name] += 1
            spawn_wheat -= cost

        # Explicitly assign every remaining villager.
        for c in components:
            if id(c) in assigned:
                continue
            if self._role(c) == "warrior":
                if c.steps_since_meal > 0 and environment.farm.wheat <= 0:
                    self._assign(environment, c, "eat")
                else:
                    self._assign(environment, c, "cave")
            else:
                self._assign(environment, c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for c in components:
            if self._role(c) == "warrior":
                warriors.append(c)
            else:
                self._assign(environment, c, "village")

        # Rank by hunger cohort so meal trips are staggered instead of having
        # every Warrior leave the Cave at the same time.
        return_candidates = []
        for index, c in enumerate(warriors):
            threshold = 3 if index % 2 == 0 else 4
            if c.steps_since_meal >= threshold:
                return_candidates.append(c)

        return_candidates.sort(
            key=lambda c: (-c.steps_since_meal, c.hp)
        )

        # When there are several Warriors, retain at least one attacker.
        # A lone Warrior must eventually return at hunger 4 to avoid starvation.
        returning = set()
        if len(warriors) == 1:
            c = warriors[0]
            if c.steps_since_meal >= 4:
                returning.add(id(c))
        elif warriors:
            max_returns = len(warriors) - 1
            for c in return_candidates[:max_returns]:
                returning.add(id(c))

        for c in warriors:
            if id(c) in returning:
                self._assign(environment, c, "village")
            else:
                self._assign(environment, c, "attack")