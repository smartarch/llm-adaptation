I’ll make combat the priority once the required spawns are scheduled: keep every well-fed Village warrior heading to the Cave, and have Cave warriors attack until they need a meal trip. The prior version could leave a returning warrior farming instead of eating promptly, or spend too many turns on spawn attempts. This version allocates affordable meals first, tries the required spawn batches without a broad food reserve, and always explicitly assigns each component.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0
        self._return_cursor = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _hunger(component):
        return int(getattr(component, "steps_since_meal", 0))

    @staticmethod
    def _hp(component):
        return int(getattr(component, "hp", 1))

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        assignments = {}

        # Default: farmers work, and warriors go to the Cave. Meals and spawn
        # groups are allocated explicitly afterward.
        for component in components:
            assignments[component] = (
                "cave" if self._role(component) == "warrior" else "farm"
            )

        # Eat only when wheat is available. A meal at hunger 5 prevents the
        # villager from reaching 6 consecutive steps without eating.
        meal_candidates = sorted(
            (c for c in components if self._hunger(c) >= 5),
            key=lambda c: (
                self._hunger(c),
                self._role(c) == "warrior",
            ),
            reverse=True,
        )
        for component in meal_candidates:
            if wheat <= 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        def schedule_spawn(kind, cost):
            nonlocal wheat

            if wheat < cost:
                return False

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                spawn_group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                spawn_group = "spawn farmer"

            # Prefer farmers as spawners so warriors can reach the Cave.
            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
            ]
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    self._hunger(c),
                )
            )
            if len(candidates) < 2:
                return False

            for component in candidates[:2]:
                assignments[component] = spawn_group

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_batches += 1
            else:
                self._farmer_spawn_batches += 1
            return True

        # Schedule one batch per call: the spawn group requires two villagers
        # and must not be assigned on top of their meals or another batch.
        if self._warrior_spawn_batches < 2:
            schedule_spawn("warrior", 12)
        elif self._farmer_spawn_batches < 1:
            schedule_spawn("farmer", 10)

        # At the deadline, prioritize moving Village warriors to the Cave
        # rather than spending their assignment on a spawn action.
        if step >= 29:
            for component in components:
                if self._role(component) == "warrior":
                    assignments[component] = "cave"

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        living_warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # At hunger 4, return for a meal before starvation. At hunger 3,
        # stagger one early return if nobody is already due.
        returning = {
            id(c) for c in living_warriors
            if self._hunger(c) >= 4
        }

        if not returning:
            eligible = [
                c for c in living_warriors
                if self._hunger(c) >= 3
            ]
            if eligible:
                eligible.sort(
                    key=lambda c: (self._hunger(c), self._hp(c)),
                    reverse=True,
                )
                returning.add( id(eligible[self._return_cursor % len(eligible)]) )
                self._return_cursor += 1

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```