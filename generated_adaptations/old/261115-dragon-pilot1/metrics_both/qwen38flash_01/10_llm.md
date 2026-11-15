

## Analysis

The 24-turn regression was caused by:
1. **Conservative spawning**: Keeping half the farmers farming slowed warrior buildup. The 20.3-turn solution spawned more aggressively early.
2. **Farmer eat threshold at 5**: The 20.3 solution used 4, which prevented emergency eating that disrupts farming.
3. **Wheat tracking was actually wrong**: `environment.farm.wheat` is a snapshot before deductions. Checking `wheat >= 12` then `wheat >= 24` in the 20.3 code correctly tested affordability of 1 vs 2 pairs.

## Strategy

- **Warriors**: Same proven cycle — eat at ≥2, cave at ≤1, attack at ≤3, return at ≥4 (3 attacks per 6-step cycle)
- **Farmers**: Eat at ≥4 (proven), spawn warriors aggressively early (up to wheat//12 pairs while keeping ≥1 farmer farming), farm rest
- **Cave**: Attack ≤3, return ≥4, stagger protection to prevent all-leaving simultaneously
- **Aggressive early spawning**: Spawn as many warrior pairs as wheat allows in first 10 steps to build up attacking force fast

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

        # === WARRIORS: optimal 3-attack / 6-step cycle ===
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # === FARMERS: eat at >=4 to prevent emergency, spawn warriors, farm rest ===
        free_farmers = []
        for c in farmers:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
            else:
                free_farmers.append(c)

        # Spawning: use up to (len-1)//2 farmers so at least 1 farms
        # Affordable pairs = wheat // 12 (wheat is pre-deduction snapshot)
        max_spawn_pairs = min(
            max(0, (len(free_farmers) - 1) // 2),
            int(wheat) // 12
        )

        for i in range(max_spawn_pairs):
            environment.assign_group(free_farmers[2 * i], "spawn warrior")
            environment.assign_group(free_farmers[2 * i + 1], "spawn warrior")

        # All remaining free farmers: farm to produce wheat
        for i in range(2 * max_spawn_pairs, len(free_farmers)):
            environment.assign_group(free_farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave (edge case): return to village
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack while steps_since_meal <= 3; return at >= 4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger: prevent all warriors leaving simultaneously (dragon regen guard)
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```