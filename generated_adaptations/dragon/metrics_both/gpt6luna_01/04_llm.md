The previous strategy could send Warriors back to eat in synchronized groups, leaving the Dragon unattended. This version staggers Cave departures: at hunger level 4, it sends only one Warrior back when another can keep attacking; Warriors at level 5 must return to avoid missing their meal deadline. In the Village, Warriors eat before departing again, while Farmers eat when needed and otherwise farm or spawn villagers. Spawning is limited to two of each type and preserves wheat needed for imminent meals.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next_rank = 0
        self._ranks = {}
        self._spawned = {"spawn farmer": 0, "spawn warrior": 0}
        self._entering_cave = set()

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def _rank(self, component):
        key = id(component)
        if key not in self._ranks:
            self._ranks[key] = self._next_rank
            self._next_rank += 1
        return self._ranks[key]

    def assign_in_village(self, components, environment, group_ids, step: int):
        warriors = []
        farmers = []

        for component in components:
            if self._role(component) == "warrior":
                self._rank(component)
                warriors.append(component)
            else:
                farmers.append(component)

        assigned = set()
        wheat = max(0, environment.farm.wheat)

        # Feed Warriors early enough that they can travel to the Cave and attack,
        # and feed Farmers before they reach the starvation limit.
        for component in warriors:
            if component.steps_since_meal >= 3 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Reserve wheat for Farmers who will need food soon; spend only the
        # remaining wheat on spawns.
        meal_reserve = sum(
            1 for c in farmers
            if id(c) not in assigned and c.steps_since_meal >= 4
        )
        available = max(0, wheat - meal_reserve)

        spawn_candidates = [
            c for c in farmers if id(c) not in assigned
        ]
        # Prefer using healthier, recently fed Farmers for spawn groups.
        spawn_candidates.sort(
            key=lambda c: (c.steps_since_meal, -c.hp)
        )

        while len(spawn_candidates) >= 2:
            outstanding = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if not outstanding:
                break

            # Alternate types where possible, favoring Warriors on ties.
            name = min(
                outstanding,
                key=lambda n: (
                    self._spawned[n],
                    0 if n == "spawn warrior" else 1,
                ),
            )
            cost = 12 if name == "spawn warrior" else 10
            if available < cost:
                break

            pair = spawn_candidates[:2]
            spawn_candidates = spawn_candidates[2:]
            for component in pair:
                self._assign(environment, component, name)
                assigned.add(id(component))

            self._spawned[name] += 1
            available -= cost

        for component in components:
            if id(component) in assigned:
                continue

            if self._role(component) == "warrior":
                self._assign(environment, component, "cave")
                self._entering_cave.add(id(component))
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components if self._role(c) == "warrior"
        ]

        # A Warrior arriving from the Village must get an attack opportunity.
        for component in components:
            if self._role(component) != "warrior":
                self._assign(environment, component, "village")
            elif id(component) in self._entering_cave:
                self._entering_cave.discard(id(component))
                self._assign(environment, component, "attack")

        active = [
            c for c in warriors if id(c) not in self._entering_cave
        ]
        if not active:
            return

        # At hunger 5 a Warrior must return now. At hunger 4, stagger returns
        # and keep at least one other Warrior attacking when possible.
        mandatory = [
            c for c in active if c.steps_since_meal >= 5
        ]
        candidates = [
            c for c in active
            if 4 <= c.steps_since_meal < 5
        ]
        candidates.sort(
            key=lambda c: (-c.steps_since_meal, self._rank(c))
        )

        returning = list(mandatory)
        remaining = len(active) - len(returning)

        if remaining > 1 and candidates:
            returning.append(candidates[0])
        elif remaining == 1 and candidates:
            # Do not create an avoidable gap in attacks; the Warrior can
            # attack once more and return on the next assignment.
            pass

        returning_ids = {id(c) for c in returning}
        for component in active:
            if id(component) in returning_ids:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```