## Strategy Description

**Key ideas:**

1. **Eating first:** Anyone whose `steps_since_meal >= 4` is at risk (starvation starts at 6), so they must eat (in the Village) or return to the Village (from the Cave) to eat next step.
2. **Village:** Farmers mostly farm to build up wheat; warriors in the Village travel to the Cave. When wheat is high enough (≥ 12 + food reserve), pairs of villagers spawn warriors to grow the army; if wheat is plentiful (≥ 10 extra), we also spawn farmers to grow the economy. Everyone eats before anything else.
3. **Cave:** All healthy villagers attack the Dragon; starving ones head back to the Village to eat. Warriors keep attacking; farmers only attack if we have plenty of attackers.
4. The Dragon's regeneration means we should keep a constant stream of attackers once combat starts, so villagers with low starvation risk stay in the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers_in_village = [c for c in components if c.role == "Farmer"]
        warriors_in_village = [c for c in components if c.role == "Warrior"]

        assigned = []

        # 1) Hungry villagers eat first
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                assigned.append(c)

        remaining = [c for c in components if c not in assigned]

        # 2) Warriors travel to the Cave
        for c in warriors_in_village:
            if c not in assigned:
                environment.assign_group(c, "cave")
                assigned.append(c)

        remaining = [c for c in components if c not in assigned]

        # 3) Spawn new villagers when we can afford it (keep food reserve)
        spawned_pairs = 0
        i = 0
        while wheat >= 12 and i + 1 < len(remaining) and spawned_pairs < 2:
            environment.assign_group(remaining[i], "spawn warrior")
            environment.assign_group(remaining[i + 1], "spawn warrior")
            wheat -= 12
            i += 2
            spawned_pairs += 1

        remaining = remaining[i:]

        # 4) If very rich, spawn farmers too (economy growth)
        i = 0
        if wheat >= 22:  # 10 for farmer + keep reserve for meals/warriors
            while wheat >= 10 and i + 1 < len(remaining):
                environment.assign_group(remaining[i], "spawn farmer")
                environment.assign_group(remaining[i + 1], "spawn farmer")
                wheat -= 10
                i += 2
            remaining = remaining[i:]

        # 5) Everyone else farms
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = [c for c in components if c.steps_since_meal < 4]
        returners = [c for c in components if c.steps_since_meal >= 4]

        # Keep enough attackers so the Dragon doesn't regenerate; prefer warriors
        attackers.sort(key=lambda c: 0 if c.role == "Warrior" else 1)

        # Everyone healthy attacks; starving ones go home to eat
        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")
```

Notes on the design:
- The threshold `steps_since_meal >= 4` leaves a 2-step safety margin: a villager sent home from the Cave arrives in the Village the next step and can still eat before hitting 6.
- Spawning warriors is prioritized (they kill the Dragon faster); spawning farmers only happens with a large wheat surplus.
- Warriors in the Village are always sent to the Cave so that the attack pressure is continuous and the Dragon's 5 HP/step regeneration rarely kicks in.