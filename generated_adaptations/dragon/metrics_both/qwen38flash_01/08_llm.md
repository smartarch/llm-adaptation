

## Analysis of the Regression

The 67% win rate was caused by the greedy `while` loop for spawning that used **stale wheat values** — it kept spawning warrior pairs without decrementing the tracked wheat amount, overcommitting resources and starving farmers. Additionally, spawning all free farmers left no one to farm wheat.

## Strategy Changes

1. **Fixed wheat tracking**: Decrement a local `wheat` counter with each spawn pair consumed.
2. **Keep farmers farming**: Limit spawning to use at most half of free farmers, keeping the rest producing wheat.
3. **Warrior cycle preserved** (the core of the 100% solution): Eat at steps≥2, cave at steps≤1, attack at steps≤3, return at steps≥4. This gives 2 attacks per 6-step cycle.
4. **Stagger protection**: Never let all warriors leave cave simultaneously.
5. **Farmers eat at steps≥5** (last safe step) to maximize wheat for warrior spawning.
6. **Aggressive but safe spawning**: Spawn as many warrior pairs as possible per step while tracking wheat and keeping ≥1 farmer farming.

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

        # --- WARRIORS in village ---
        # Optimal cycle: eat(>=2) -> cave(<=1) -> attack(2,3) -> return(>=4)
        # Eating at step 2 resets so next trip yields 2 attacks (arrive at steps=2)
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # --- FARMERS in village ---
        # Eat at steps>=5 (last safe step before starvation at 6)
        free_farmers = []
        for c in farmers:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
            else:
                free_farmers.append(c)

        # --- SPAWNING: aggressively spawn warriors, but keep >=1 farming ---
        remaining = list(free_farmers)
        # Use at most half of free farmers for spawning (keep rest farming)
        max_spawn_pairs = max(0, len(remaining) // 2)
        # But always keep at least 1 farmer farming
        while len(remaining) >= 2 and max_spawn_pairs > 0 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
            wheat -= 12  # Track consumed wheat
            max_spawn_pairs -= 1

        # Remaining farmers produce wheat
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave (edge case): send back immediately
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack while steps_since_meal <= 3 (2 attacks per trip: arrive at 2, attack 2-3)
        # Return at steps_since_meal >= 4 (arrive village at 5, eat immediately)
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger protection: if ALL warriors must leave and NONE can attack,
        # keep the one with the LOWEST steps_since_meal to prevent regen gap.
        # They'll go to village next step (steps=5), arrive at 6, eat. 1 HP lost.
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```