I’ll fix meal accounting so wheat is charged only when a meal is actually assigned, and make spawning depend on successful scheduled batches rather than assuming extra batch attempts will help. The strategy keeps farmers producing food, uses available surplus to add warriors before a farmer, and rotates warriors back for meals while leaving others attacking whenever possible. It explicitly assigns every component on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0

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

        # Set a non-eating default first; meals are allocated below only when
        # their wheat cost can actually be paid.
        for component in components:
            role = self._role(component)
            if role == "warrior":
                assignments[component] = (
                    "farm" if self._hunger(component) >= 3 else "cave"
                )
            else:
                assignments[component] = "farm"

        # Prioritize warriors, who also need to travel back to the Cave, then
        # feed the hungriest villagers. Decrement wheat exactly once per meal.
        meal_candidates = [
            c for c in components
            if self._hunger(c) >= (
                3 if self._role(c) == "warrior" else 5
            )
        ]
        meal_candidates.sort(
            key=lambda c: (
                self._role(c) == "warrior",
                self._hunger(c),
            ),
            reverse=True,
        )

        for component in meal_candidates:
            if wheat <= 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        # Protect food for villagers close to needing a meal. This reserve is
        # based on urgency, not the whole population, so it does not block
        # early warrior recruitment.
        meal_reserve = sum(
            1 for c in components
            if assignments[c] != "eat"
            and self._hunger(c) >= (
                3 if self._role(c) == "warrior" else 4
            )
        )

        def spawn_batch(kind, cost):
            nonlocal wheat

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                spawn_group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                spawn_group = "spawn farmer"

            if wheat < cost + meal_reserve:
                return False

            # Prefer farmers as spawners, preserving warriors for combat.
            # Only use components not already committed to eating/spawning.
            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
            ]
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    -self._hunger(c),
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

        # Schedule at most one batch per call, so the same workforce and wheat
        # are not committed to several spawn actions in one step.
        if self._warrior_spawn_batches < 2:
            spawn_batch("warrior", 12)
        elif self._farmer_spawn_batches < 1:
            spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        living_warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # At hunger 4, return all affected warriors to satisfy the meal safety
        # constraint. At hunger 3, stagger returns when multiple warriors are
        # available so that someone can continue attacking.
        returning = {
            id(c) for c in living_warriors
            if self._hunger(c) >= 4
        }

        if len(living_warriors) >= 2:
            hunger_three = sorted(
                (
                    c for c in living_warriors
                    if self._hunger(c) == 3 and id(c) not in returning
                ),
                key=lambda c: self._hp(c),
            )
            if hunger_three and not returning:
                returning.add(id(hunger_three[0]))

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```