I’d simplify the schedule and avoid relying on “newly arrived” bookkeeping: a Warrior in the Village eats if it has missed any meal, otherwise it heads to the Cave; a Warrior in the Cave attacks until a staggered return is needed. Cave returns are limited to one Warrior per assignment call where possible, so others can keep attacking. Farmers eat before starvation, and spawning uses only fed Farmers and wheat left after reserving food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rank_by_id = {}
        self._next_rank = 0
        self._spawned = {
            "spawn warrior": 0,
            "spawn farmer": 0,
        }

    @staticmethod
    def _role(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def _rank(self, component):
        key = id(component)
        if key not in self._rank_by_id:
            self._rank_by_id[key] = self._next_rank
            self._next_rank += 1
        return self._rank_by_id[key]

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, environment.farm.wheat)
        assigned = set()
        farmers = []

        # Warriors returning to the Village eat first, then head back to the Cave
        # on a later assignment. This leaves them fed for the trip and attack.
        for c in components:
            if self._role(c) == "warrior":
                self._rank(c)
                if c.steps_since_meal > 0 and wheat > 0:
                    self._assign(environment, c, "eat")
                    assigned.add(id(c))
                    wheat -= 1
            else:
                farmers.append(c)

        # Farmers must eat by hunger 5 to avoid reaching the starvation limit.
        for c in farmers:
            if c.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, c, "eat")
                assigned.add(id(c))
                wheat -= 1

        # Keep wheat available for Farmers who will need food soon.
        meal_reserve = sum(
            1 for c in farmers
            if id(c) not in assigned and c.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - meal_reserve)

        # Do not use hungry Farmers for spawning; they need to remain available
        # to eat or farm.
        spawn_candidates = [
            c for c in farmers
            if id(c) not in assigned and c.steps_since_meal < 4
        ]
        spawn_candidates.sort(
            key=lambda c: (c.steps_since_meal, -c.hp)
        )

        # Prioritize Warriors, but also spawn Farmers when there is enough
        # wheat and a pair of suitable villagers.
        while len(spawn_candidates) >= 2:
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

            pair = spawn_candidates[:2]
            spawn_candidates = spawn_candidates[2:]
            for c in pair:
                self._assign(environment, c, name)
                assigned.add(id(c))

            self._spawned[name] += 1
            spawn_wheat -= cost

        # Explicitly assign every component not already assigned.
        for c in components:
            if id(c) in assigned:
                continue
            if self._role(c) == "warrior":
                self._assign(environment, c, "cave")
            else:
                self._assign(environment, c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for c in components:
            if self._role(c) == "warrior":
                self._rank(c)
                warriors.append(c)
            else:
                self._assign(environment, c, "village")

        if not warriors:
            return

        # Choose at most one returnee per call when possible. Higher hunger
        # takes priority; the stable rank breaks ties to stagger cohorts.
        return_candidates = [c for c in warriors if c.steps_since_meal >= 3]
        return_candidates.sort(
            key=lambda c: (-c.steps_since_meal, self._rank(c))
        )

        returning = None
        if return_candidates:
            # If several Warriors are present, keep at least one attacking.
            # A lone Warrior returns at hunger 4 to avoid starvation.
            if len(warriors) > 1 or return_candidates[0].steps_since_meal >= 4:
                returning = return_candidates[0]

        for c in warriors:
            if c is returning:
                self._assign(environment, c, "village")
            else:
                self._assign(environment, c, "attack")
```