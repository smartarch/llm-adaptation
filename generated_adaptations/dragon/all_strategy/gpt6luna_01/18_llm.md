The meal failures indicate that spawning was still allowed to draw down food reserves needed later. This version prioritizes meals, delays spawning until there is a substantial wheat surplus, and returns Cave Warriors early enough to eat. It also explicitly assigns every villager, including when there is not enough wheat to eat or spawn.

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

        # Eat at age 4 when food is available. At age 3, eat only if there is
        # enough wheat for the other villagers who are close to needing food.
        due = sorted(
            (c for c in components if self._age(c) >= 4),
            key=self._age,
            reverse=True,
        )
        for component in due:
            if wheat > 0:
                self._assign(environment, component, "eat")
                wheat -= 1
                assigned.add(id(component))

        near_due = sorted(
            (c for c in components
             if id(c) not in assigned and self._age(c) == 3),
            key=self._age,
            reverse=True,
        )
        for component in near_due:
            other_due = sum(
                1 for c in components
                if id(c) not in assigned and self._age(c) >= 3
            )
            if wheat >= other_due + 8:
                self._assign(environment, component, "eat")
                wheat -= 1
                assigned.add(id(component))

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Send Warriors back toward the Cave if they are fed. If they are due
        # for a meal but there is no wheat, keep them in the Village to work.
        for warrior in warriors:
            if id(warrior) in assigned:
                continue
            if self._age(warrior) >= 4:
                self._assign(environment, warrior, "farm")
            else:
                self._assign(environment, warrior, "cave")
            assigned.add(id(warrior))

        available_farmers = [f for f in farmers if id(f) not in assigned]

        # Only spawn from a clear surplus: keep a reserve for meals, including
        # Warriors that may return from the Cave on following steps.
        reserve = max(18, 2 * len(components) + 8)
        spawn_group = None

        if len(available_farmers) >= 2:
            if self.farmer_spawn_events < 2 and wheat >= 10 + reserve:
                spawn_group = "spawn farmer"
            elif (
                self.warrior_spawn_events < 6
                and wheat >= 12 + reserve
                and (self.farmer_spawn_events >= 2 or len(warriors) == 0)
            ):
                spawn_group = "spawn warrior"

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                assigned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1

        # Farm with everyone not assigned to eat, travel, or spawn.
        for component in components:
            if id(component) not in assigned:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]

        # Return a Warrior at age 4, or earlier if another Warrior can keep
        # attacking. This staggers meal trips and maintains attack pressure.
        due = sorted(
            (w for w in warriors if self._age(w) >= 4),
            key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
            reverse=True,
        )
        returning_id = id(due[0]) if due else None

        if returning_id is None:
            early = sorted(
                (w for w in warriors if self._age(w) >= 3),
                key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
                reverse=True,
            )
            for candidate in early:
                remaining_attackers = [
                    w for w in warriors
                    if w is not candidate
                    and getattr(w, "hp", 0) > 0
                    and self._age(w) < 4
                ]
                if remaining_attackers:
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