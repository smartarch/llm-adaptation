The main issue was that the previous strategy did not reliably create warriors, so the Dragon could outlast the villagers. This version prioritizes spawning a warrior when none are alive, then builds toward a small attacking force while retaining villagers to produce food. It also sends cave villagers back early enough to eat and withdraws critically wounded attackers. Every component is explicitly assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    @staticmethod
    def _value(component, name, default=0):
        return getattr(component, name, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._value(environment.farm, "wheat", 0))
        dragon_hp = max(0, self._value(environment.dragon, "hp", 0))

        all_warriors = list(getattr(environment, "warriors", []))
        all_farmers = list(getattr(environment, "farmers", []))
        living_count = len(all_warriors) + len(all_farmers)
        warrior_count = len(all_warriors)

        assigned = []
        remaining = list(villagers)

        def put(component, group):
            self._assign(environment, component, group)
            assigned.append(component)
            remaining.remove(component)

        # Eat before the starvation threshold. Reserve the rest of the wheat
        # when deciding whether there is enough to spawn.
        eaters = sorted(
            (v for v in remaining
             if self._value(v, "steps_since_meal", 0) >= 4),
            key=lambda v: (
                self._value(v, "steps_since_meal", 0),
                -self._value(v, "hp", 0),
            ),
            reverse=True,
        )
        for v in eaters:
            if wheat <= 0:
                break
            put(v, "eat")
            wheat -= 1

        local_farmers = [
            v for v in remaining
            if self._value(v, "role", "") == "Farmer"
        ]

        # Choose one spawn action per step. A first Warrior is the priority:
        # without one, the Dragon cannot be killed.
        spawn_group = None
        if dragon_hp > 0 and warrior_count == 0:
            if wheat >= 12 + living_count and len(remaining) >= 2:
                spawn_group = "spawn warrior"
        elif dragon_hp > 0 and warrior_count < 3:
            if wheat >= 12 + living_count and len(remaining) >= 2:
                spawn_group = "spawn warrior"

        # Grow the population to improve the food economy when a Warrior is
        # already available and a Farmer can be spawned with a meal reserve.
        if (spawn_group is None and dragon_hp > 0 and living_count < 5
                and wheat >= 10 + living_count
                and len(local_farmers) >= 2):
            spawn_group = "spawn farmer"

        if spawn_group is not None:
            # Prefer Farmers for spawning, leaving other villagers available
            # to farm or travel to the Cave.
            spawners = sorted(
                remaining,
                key=lambda v: (
                    self._value(v, "role", "") != "Farmer",
                    self._value(v, "steps_since_meal", 0),
                ),
            )[:2]
            for v in spawners:
                put(v, spawn_group)

        # Send every available Warrior toward the Dragon. Keep Farmers working
        # unless the Dragon is nearly dead and extra damage may finish it.
        for v in list(remaining):
            role = self._value(v, "role", "")
            hp = self._value(v, "hp", 0)
            age = self._value(v, "steps_since_meal", 0)

            if role == "Warrior" and hp > 0 and age < 4 and dragon_hp > 0:
                put(v, "cave")
            elif role == "Farmer" and dragon_hp <= 12 and hp > 0 and age < 4:
                put(v, "cave")
            else:
                put(v, "farm")

        # Defensive explicit assignment in case component collections have
        # unusual behavior.
        for v in villagers:
            if v not in assigned:
                self._assign(environment, v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, self._value(environment.dragon, "hp", 0))

        for v in components:
            age = self._value(v, "steps_since_meal", 0)
            hp = self._value(v, "hp", 0)
            role = self._value(v, "role", "")

            if dragon_hp <= 0:
                self._assign(environment, v, "village")
            elif age >= 4 or hp <= 2 or role == "Farmer":
                # Farmers contribute little damage and are more valuable
                # sustaining the Village's food supply.
                self._assign(environment, v, "village")
            else:
                self._assign(environment, v, "attack")
```