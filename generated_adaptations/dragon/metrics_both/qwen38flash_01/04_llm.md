

## Analysis of Issues

The 33% win rate suggests problems with:
1. **Too many warriors going to cave hungry** (only getting 1 attack per trip)
2. **Poor staggering** - warriors leave cave simultaneously, creating attack gaps where dragon regenerates
3. **Slow spawning** - not enough warriors attacking simultaneously
4. **Overly conservative eating** - farmers eating too often reduces wheat/spawning

## Improved Strategy

- Warriors go to cave ONLY at steps_since_meal ≤ 1 (guaranteeing 2-3 attacks per trip)
- Warriors eat at steps_since_meal = 2 (to reset into optimal 3-attack cycle)
- In cave: attack at steps ≤ 3, return at steps ≥ 4 (never starve)
- **Critical**: prevent all warriors leaving cave simultaneously (stagger returns)
- Aggressive warrior spawning early, farmer spawning for wheat production
- Farmers eat at steps ≥ 5, farm otherwise, spawn warriors aggressively

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # === WARriors in village ===
        # Must eat at steps_since_meal >= 5 (game constraint)
        # Must eat at steps >= 3 (rule: can't go to cave at >= 3)
        # Eat at steps == 2 to reset for optimal 3-attack cycle
        # Go to cave at steps 0 or 1 (arrives at cave with steps 1 or 2 → 2-3 attacks)

        warriors_to_eat = []
        warriors_to_cave = []

        for c in warriors:
            if c.steps_since_meal >= 3:
                # Must eat (constraint: >= 3 can't go to cave)
                warriors_to_eat.append(c)
            elif c.steps_since_meal == 2:
                # Eat now to get optimal cycle (arrive cave at steps=1, get 3 attacks)
                warriors_to_eat.append(c)
            elif c.steps_since_meal <= 1:
                # Go to cave - will arrive at steps=1 or 2
                warriors_to_cave.append(c)
            else:
                # steps >= 5 somehow, forced eat
                warriors_to_eat.append(c)

        for c in warriors_to_eat:
            environment.assign_group(c, "eat")
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # === FARMERS in village ===
        # Must eat at steps >= 5
        # Prefer to eat at steps 4 for planning
        # Otherwise: spawn warriors (high priority), spawn farmers, or farm

        farmers_to_eat = []
        farmers_free = []

        for c in farmers:
            if c.steps_since_meal >= 4:
                farmers_to_eat.append(c)
            else:
                farmers_free.append(c)

        for c in farmers_to_eat:
            environment.assign_group(c, "eat")

        # Spawning strategy: aggressively spawn warriors early
        # Need 2 farmers in spawn group + wheat
        remaining = list(farmers_free)

        if step <= 22 and len(remaining) >= 2:
            # Priority 1: spawn warrior (12 wheat)
            if wheat >= 12:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
                # Try second pair of warriors
                if len(remaining) >= 2 and wheat >= 24:
                    environment.assign_group(remaining[0], "spawn warrior")
                    environment.assign_group(remaining[1], "spawn warrior")
                    remaining = remaining[2:]
                elif len(remaining) >= 2 and wheat >= 22:
                    environment.assign_group(remaining[0], "spawn farmer")
                    environment.assign_group(remaining[1], "spawn farmer")
                    remaining = remaining[2:]
            elif wheat >= 10:
                # Can't afford warrior, spawn farmer for more wheat
                environment.assign_group(remaining[0], "spawn farmer")
                environment.assign_group(remaining[1], "spawn farmer")
                remaining = remaining[2:]

        # All remaining farmers: farm
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers in cave (edge case): send back immediately
        for c in farmers:
            environment.assign_group(c, "village")

        if not warriors:
            return

        # Warriors in cave:
        # Attack at steps_since_meal <= 3 (arrive at cave with steps 1-2, attack at 2-4)
        # Return to village at steps_since_meal >= 4

        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger prevention: if ALL warriors must return and NONE can attack,
        # keep the one with the LOWEST steps_since_meal to attack one more time
        # (it'll go to village next step at steps=5, arrive at 6, eat - 1 HP loss acceptable)
        if not can_attack and must_return:
            # Sort by steps_since_meal, keep the freshest one to attack
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```