The failures came from waiting too long to feed villagers and sending too many warriors back to eat at once, leaving the Dragon unattacked. This revision feeds villagers when their meal is due (at five steps), staggers cave returns, and spawns additional warriors while still making two Farmer spawn attempts. A warrior in the Village eats before returning to the Cave if hungry.

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
        wheat = getattr(environment.farm, "wheat", 0)
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Eat at five steps without a meal, before the villager becomes hungry.
        for component in components:
            if self._age(component) >= 5:
                self._assign(environment, component, "eat")
                wheat = max(0, wheat - 1)

        # Fed Warriors should return to the Cave promptly.
        for warrior in warriors:
            if self._age(warrior) < 5:
                self._assign(environment, warrior, "cave")

        available_farmers = [
            f for f in farmers if self._age(f) < 5
        ]
        meals_due = sum(1 for c in components if self._age(c) >= 5)

        # Try to establish the requested Farmer workforce, then prioritize
        # Warriors so there are enough attackers to rotate for meals.
        spawn_group = None
        spawn_cost = 0
        if (
            self.farmer_spawn_events == 0
            and len(available_farmers) >= 2
            and wheat >= 10 + meals_due
        ):
            spawn_group, spawn_cost = "spawn farmer", 10
        elif (
            self.warrior_spawn_events < 2
            and len(available_farmers) >= 2
            and wheat >= 12 + meals_due
        ):
            spawn_group, spawn_cost = "spawn warrior", 12
        elif (
            self.farmer_spawn_events < 2
            and len(available_farmers) >= 2
            and wheat >= 10 + meals_due
        ):
            spawn_group, spawn_cost = "spawn farmer", 10
        elif (
            self.warrior_spawn_events < 5
            and len(available_farmers) >= 2
            and wheat >= 12 + meals_due
        ):
            spawn_group, spawn_cost = "spawn warrior", 12

        spawned = set()
        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                spawned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1

            wheat = max(0, wheat - spawn_cost)

        for farmer in farmers:
            if self._age(farmer) >= 5 or id(farmer) in spawned:
                continue
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]
        due = sorted(
            (w for w in warriors if self._age(w) >= 4),
            key=self._age,
            reverse=True,
        )

        # Send only one Warrior back at a time when another can keep attacking.
        returning = due[0] if due and len(warriors) > 1 else None

        for warrior in warriors:
            if warrior is returning:
                self._assign(environment, warrior, "village")
            elif getattr(warrior, "hp", 0) > 0 and self._age(warrior) < 6:
                self._assign(environment, warrior, "attack")
            else:
                self._assign(environment, warrior, "village")

        # Farmers are not intended to be in the Cave.
        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
```