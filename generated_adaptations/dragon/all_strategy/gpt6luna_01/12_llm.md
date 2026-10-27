The attack gaps are consistent with Warriors returning to eat in a synchronized group. This version staggers Cave returns to at most one Warrior per step, while letting the others attack; it also sends Warriors back at age 4 so they have time to travel and eat. In the Village, meals take priority over spawning, and spawning targets two Farmer events and then builds the Warrior force—unless there are no Warriors yet, in which case it prioritizes a Warrior spawn.

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

        # Prioritize meals, and never request a meal if there is no wheat.
        # Age 5 is the last safe opportunity to eat.
        meal_candidates = sorted(
            (c for c in components if self._age(c) >= 5),
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

        # A Warrior in the Village who cannot eat yet should return to fight.
        # If a meal is due but wheat is unavailable, farming is the safe
        # fallback rather than sending a starving villager away.
        for warrior in warriors:
            if id(warrior) in assigned:
                continue
            if self._age(warrior) >= 5:
                self._assign(environment, warrior, "farm")
            else:
                self._assign(environment, warrior, "cave")
            assigned.add(id(warrior))

        available_farmers = [f for f in farmers if id(f) not in assigned]

        # Reserve enough wheat for villagers who are about to need meals.
        imminent_meals = sum(
            1 for c in components
            if id(c) not in assigned and self._age(c) >= 4
        )
        spawn_group = None
        spawn_cost = 0

        if len(available_farmers) >= 2:
            # If there is no Warrior force yet, create one immediately.
            if len(warriors) == 0 and self.warrior_spawn_events < 8:
                if wheat >= 12 + imminent_meals:
                    spawn_group, spawn_cost = "spawn warrior", 12
            # Otherwise establish the requested Farmer workforce first.
            elif self.farmer_spawn_events < 2:
                if wheat >= 10 + imminent_meals:
                    spawn_group, spawn_cost = "spawn farmer", 10
            # Then invest remaining farmer pairs in Warriors.
            elif self.warrior_spawn_events < 8:
                if wheat >= 12 + imminent_meals:
                    spawn_group, spawn_cost = "spawn warrior", 12

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                assigned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1

            wheat = max(0, wheat - spawn_cost)

        # Assign every remaining component, including farmers when there is
        # not enough food to spawn or eat.
        for component in components:
            if id(component) not in assigned:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]

        # Return only one due Warrior each step, choosing the most overdue.
        # Everyone else remains assigned to attack, preventing synchronized
        # breaks in pressure on the Dragon.
        due = sorted(
            (w for w in warriors if self._age(w) >= 4),
            key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
            reverse=True,
        )
        returning_id = id(due[0]) if due else None

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
            elif id(component) == returning_id:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```