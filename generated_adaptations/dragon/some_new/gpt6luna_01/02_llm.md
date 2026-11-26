The strategy prioritizes feeding villagers before they approach starvation, keeps at least one farmer producing wheat, and uses surplus farmers in pairs to spawn warriors when there is enough wheat. Healthy warriors in the Village are sent to attack. Cave villagers return to the Village at four steps since their last meal, leaving time to travel and eat before starving; other cave villagers keep attacking to limit the Dragon’s regeneration.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, getattr(environment.farm, "wheat", 0))

        def age(v):
            return getattr(v, "steps_since_meal", 0)

        def hp(v):
            return getattr(v, "hp", 0)

        # Feed the most urgent villagers first, subject to available wheat.
        urgent = sorted(
            (v for v in villagers if age(v) >= 4),
            key=lambda v: (age(v), -hp(v)),
            reverse=True,
        )
        assigned = set()
        for v in urgent:
            if wheat > 0:
                self._assign(environment, v, "eat")
                wheat -= 1
                assigned.add(v)

        remaining = [v for v in villagers if v not in assigned]

        # Keep villagers who are close to starvation in the Village.
        # Farming is their available non-eating action while food is scarce.
        for v in remaining[:]:
            if age(v) >= 3:
                self._assign(environment, v, "farm")
                assigned.add(v)
                remaining.remove(v)

        farmers = [v for v in remaining if getattr(v, "role", "") == "Farmer"]
        warriors = [v for v in remaining if getattr(v, "role", "") == "Warrior"]

        # Keep a farmer working so the Village can replenish its food supply.
        farm_count = min(1, len(farmers))
        for v in farmers[:farm_count]:
            self._assign(environment, v, "farm")
            assigned.add(v)

        available_farmers = farmers[farm_count:]

        # Use surplus farmers in pairs to spawn warriors when the wheat budget
        # allows it, keeping a small reserve for meals.
        affordable_pairs = max(0, (wheat - 2) // 12)
        spawn_pairs = min(len(available_farmers) // 2, affordable_pairs)
        spawn_count = 2 * spawn_pairs
        for v in available_farmers[:spawn_count]:
            self._assign(environment, v, "spawn warrior")
            assigned.add(v)

        # Send healthy warriors to the Cave. Unused farmers continue producing
        # food; if there is no remaining farmer workforce, they can help attack.
        for v in warriors:
            if v not in assigned:
                self._assign(environment, v, "cave")
                assigned.add(v)

        dragon_hp = getattr(environment.dragon, "hp", 0)
        for v in available_farmers[spawn_count:]:
            if dragon_hp <= 12 and farm_count > 0:
                self._assign(environment, v, "cave")
            else:
                self._assign(environment, v, "farm")
            assigned.add(v)

        # Explicitly assign any unusual or unhandled villagers.
        for v in villagers:
            if v not in assigned:
                self._assign(environment, v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = getattr(environment.dragon, "hp", 0)

        for v in components:
            steps_since_meal = getattr(v, "steps_since_meal", 0)

            # Return early enough to travel to the Village and eat before the
            # starvation threshold. Everyone else keeps up the attack.
            if dragon_hp > 0 and steps_since_meal >= 4:
                self._assign(environment, v, "village")
            elif dragon_hp > 0:
                self._assign(environment, v, "attack")
            else:
                self._assign(environment, v, "village")
```