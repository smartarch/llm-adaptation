The remaining failure is caused by returning the only available Warrior too early. The updated rotation only sends an age-3 or age-4 Warrior back when at least two others can keep attacking; a Warrior at age 5 still returns so they can make the meal trip in time. This preserves early attack pressure while maintaining the existing food safeguards.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_events = 0
        self.warrior_spawn_events = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0)

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        assigned = set()

        # Feed at age 4 when possible, leaving time for Warriors returning
        # from the Cave to reach the Village before the starvation warning.
        meal_candidates = sorted(
            (c for c in components if self._age(c) >= 4),
            key=self._age,
            reverse=True,
        )
        for component in meal_candidates:
            if wheat > 0:
                self._assign(environment, component, "eat")
                wheat -= 1
                assigned.add(id(component))

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for warrior in warriors:
            if id(warrior) in assigned:
                continue
            if self._age(warrior) >= 4:
                # If there is no wheat for a due meal, stay in the Village
                # and work rather than travel back to the Cave.
                self._assign(environment, warrior, "farm")
            else:
                self._assign(environment, warrior, "cave")
            assigned.add(id(warrior))

        available_farmers = [f for f in farmers if id(f) not in assigned]

        imminent_meals = sum(
            1 for c in components
            if id(c) not in assigned and self._age(c) >= 3
        )
        food_reserve = max(6, len(components) + 2) + imminent_meals

        spawn_group = None
        if len(available_farmers) >= 2:
            if len(warriors) == 0 and self.warrior_spawn_events < 8:
                if wheat >= 12 + food_reserve:
                    spawn_group = "spawn warrior"
            elif self.farmer_spawn_events < 2:
                if wheat >= 10 + food_reserve:
                    spawn_group = "spawn farmer"
            elif self.warrior_spawn_events < 8:
                if wheat >= 12 + food_reserve:
                    spawn_group = "spawn warrior"

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                assigned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1

        for component in components:
            if id(component) not in assigned:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]

        # Age-5 Warriors must begin their return trip. Earlier returns are
        # staggered only when at least two other Warriors can keep attacking.
        due = sorted(
            (w for w in warriors if self._age(w) >= 5),
            key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
            reverse=True,
        )
        returning_id = id(due[0]) if due else None

        if returning_id is None:
            early_candidates = sorted(
                (w for w in warriors if self._age(w) >= 3),
                key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
                reverse=True,
            )
            for candidate in early_candidates:
                remaining_attackers = [
                    w for w in warriors
                    if w is not candidate
                    and self._age(w) < 5
                    and getattr(w, "hp", 0) > 0
                ]
                if len(remaining_attackers) >= 2:
                    returning_id = id(candidate)
                    break

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
            elif id(component) == returning_id:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```