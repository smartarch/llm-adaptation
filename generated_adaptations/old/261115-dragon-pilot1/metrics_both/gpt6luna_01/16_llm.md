I’d prioritize keeping a steady stream of attacks over sending Warriors back to eat in lockstep. A Cave Warrior returns when hungry, but only one return trip is started per call when there are other Warriors available to attack. Warriors in the Village eat when they need a meal, then head back; Farmers eat before starvation and otherwise farm. Spawning uses pairs of available Farmers, prioritizes Warriors, and keeps a wheat buffer for food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, environment.farm.wheat)
        assigned = set()
        farmers = []

        # Warriors should eat before departing if they have gone several
        # steps without food. Otherwise send them to attack as soon as possible.
        for c in components:
            if self._role(c) == "warrior":
                if c.steps_since_meal >= 3 and wheat > 0:
                    self._assign(environment, c, "eat")
                    assigned.add(id(c))
                    wheat -= 1
                else:
                    self._assign(environment, c, "cave")
                    assigned.add(id(c))
            else:
                farmers.append(c)

        # Feed Farmers before they reach the starvation threshold.
        for c in farmers:
            if c.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, c, "eat")
                assigned.add(id(c))
                wheat -= 1

        # Keep a modest reserve for Farmers who will need to eat soon.
        reserve = sum(
            1 for c in farmers
            if id(c) not in assigned and c.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - reserve)

        candidates = [
            c for c in farmers if id(c) not in assigned
        ]
        candidates.sort(key=lambda c: (c.steps_since_meal, -c.hp))

        # Use one pair per turn, leaving remaining Farmers to produce food.
        # Build the Warrior force first, then add Farmers when wheat permits.
        if len(candidates) >= 2:
            targets = [
                name for name in ("spawn warrior", "spawn farmer")
                if self._spawned[name] < 2
            ]
            if targets:
                target = min(
                    targets,
                    key=lambda name: (
                        self._spawned[name],
                        0 if name == "spawn warrior" else 1,
                    ),
                )
                cost = 12 if target == "spawn warrior" else 10

                # Keep some food in reserve rather than spending the last wheat.
                if spawn_wheat >= cost + 2:
                    for c in candidates[:2]:
                        self._assign(environment, c, target)
                        assigned.add(id(c))
                    self._spawned[target] += 1

        # Explicitly assign every remaining component.
        for c in components:
            if id(c) in assigned:
                continue
            self._assign(environment, c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for c in components:
            if self._role(c) == "warrior":
                warriors.append(c)
            else:
                self._assign(environment, c, "village")

        if not warriors:
            return

        # Pick the hungriest Warrior for a meal trip. Leave other Warriors
        # attacking, so the Dragon is less likely to get a regeneration turn.
        eligible = [c for c in warriors if c.steps_since_meal >= 3]
        eligible.sort(
            key=lambda c: (-c.steps_since_meal, c.hp)
        )

        returning = None
        if len(warriors) == 1:
            if eligible:
                returning = eligible[0]
        elif eligible:
            returning = eligible[0]

        for c in warriors:
            if c is returning:
                self._assign(environment, c, "village")
            else:
                self._assign(environment, c, "attack")
```