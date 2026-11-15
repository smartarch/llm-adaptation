

## Strategy Improvements

To reduce the average turns from 20.3, I focused on these optimizations:

1. **Faster warrior spawning**: Spawn warriors at EVERY step where we have 2 idle farmers + 12 wheat, rather than limiting to early steps. Warriors are the only damage source, so maximize their count ASAP.

2. **Tighter attack cycle**: Warriors in cave attack at steps_since_meal 1, 2, 3 (3 attacks per trip) and return at step 4. They eat in village at step 5 immediately upon return. This is the optimal 3-attack / 6-step cycle.

3. **Minimize warrior idle time**: A warrior that just returned to village and ate goes to cave the very next step (no waiting). Warriors never sit idle in village unless forced to eat.

4. **Reduced farmer eating frequency**: Farmers eat only when truly necessary (steps ≥ 4), maximizing wheat production for warrior spawning.

5. **Spend ALL wheat on warriors early**: Don't spawn farmers unless wheat would be wasted; warriors provide the damage output needed.

6. **First attack ASAP**: Initial warriors sent to cave at step 0 → first attack at step 1.

7. **Stagger protection retained**: Never let all warriors leave cave simultaneously.

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

        # === WARRIORS ===
        # Optimal cycle: eat -> cave-travel -> attack(3) -> return-travel -> eat
        # In village, send to cave whenever steps_since_meal <= 1
        # Eat when steps_since_meal >= 2 (forces reset for optimal cycle)
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # === FARMERS ===
        # Must eat at steps >= 5; eat at 4 to be safe
        farmers_free = []
        for c in farmers:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
            else:
                farmers_free.append(c)

        # Aggressive warrior spawning: every step we can afford it
        remaining = list(farmers_free)
        # Keep at least one farmer farming to produce wheat if possible
        # Actually we want max spawning - use pairs greedily

        while len(remaining) >= 2:
            if wheat >= 12:
                # Spawn a warrior (most valuable)
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
            elif wheat >= 10 and step < 10:
                # Early game: maybe spawn farmer to boost wheat? Only if very few farmers
                if len(farmers) + (3 - len(remaining) // 2) < 3:
                    environment.assign_group(remaining[0], "spawn farmer")
                    environment.assign_group(remaining[1], "spawn farmer")
                    remaining = remaining[2:]
                else:
                    break
            else:
                break

        # Remaining farmers farm
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers in cave (edge case): go back
        for c in farmers:
            environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack while steps_since_meal <= 3; return at 4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger protection: never let dragon go unattacked
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```