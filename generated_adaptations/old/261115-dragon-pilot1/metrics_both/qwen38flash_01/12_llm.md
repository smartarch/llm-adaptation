

## Analysis

The 0% win rate was caused by two bugs:
1. **Farmer eat threshold changed to `>= 4`**: This made farmers eat too often, producing less wheat, which meant not enough wheat to spawn warriors. Combined with the spawning formula, almost no warriors got spawned.
2. **Spawning kept 1 farmer farming**: With initial ~2 farmers, `(n_free - 1) // 2 = 0`, meaning **zero** warriors ever spawned.

The proven 20.3-turn solution used `len(free) // 2` (ALL free farmers available for spawning) and farmer eat at `>= 5` (maximum farming time). The formula version must match this exactly.

## Strategy (reverting to proven 20.3 approach, cleaned up)

- **Warriors**: eat at ssm≥2, go to cave at ssm≤1. In cave: attack at ssm≤3, return at ssm≥4. This gives 3 attacks per 6-step cycle.
- **Farmers**: eat only at ssm≥5 (max wheat production). All free farmers spawn warriors aggressively.
- **Stagger protection**: never let all cave warriors leave simultaneously.
- **Wheat tracking**: `int(wheat) // 12` correctly caps affordable spawn pairs.

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

        # Warriors: optimal 3-attack / 6-step cycle
        # ssm 0-1 → go to cave (arrive cave, attack at ssm 1,2,3 or 2,3,4)
        # ssm >= 2 → eat (resets for next optimal cycle)
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # Farmers: eat at ssm>=5 (max farming = 4 steps of 5 wheat = 20 wheat/cycle)
        free = []
        for c in farmers:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
            else:
                free.append(c)

        # Aggressive warrior spawning: use ALL free farmers, track wheat correctly
        max_pairs = min(len(free) // 2, int(wheat) // 12)
        max_pairs = max(0, max_pairs)

        for i in range(max_pairs):
            environment.assign_group(free[2 * i], "spawn warrior")
            environment.assign_group(free[2 * i + 1], "spawn warrior")

        # Remaining farmers produce wheat
        for i in range(2 * max_pairs, len(free)):
            environment.assign_group(free[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave (edge case): return to village immediately
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack while ssm <= 3 (3 attacks per trip), return at ssm >= 4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger: if ALL warriors must leave and NONE can attack,
        # keep the freshest one to prevent >2 step attack gap (dragon regen guard)
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```