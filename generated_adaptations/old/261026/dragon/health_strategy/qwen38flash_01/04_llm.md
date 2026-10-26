

## Analysis of Failures

Looking at the game data:
- **Game 1**: Stalls at 8 HP (14 warrior-attacks done, then all warriors died with no replacements)
- **Game 2**: Won in 9 steps (lucky with enough warriors surviving)
- **Game 3**: Stalls at 29 HP (only ~7 warrior-attacks, then all died)

**Root cause**: Warriors die to dragon counter-attacks and **no replenishment pipeline exists**. My original code only spawned 2 warriors total, then stopped. I need continuous warrior spawning throughout the game.

## Improved Strategy

1. **Immediate deployment**: Warriors always go to cave and attack — no delay.
2. **Continuous warrior spawning**: Not limited to 2. Spawn as many warriors as wheat/farmers allow every step, keeping a minimum of 2 farmers farming.
3. **Early farmer spawn**: Spawn 2 farmers early to grow the wheat economy.
4. **Proper wheat budgeting**: Track wheat spending within a step since `environment.farm.wheat` doesn't update mid-assignment.
5. **No farmers in cave**: Farmers are too fragile (4 HP) and deal only 1 damage. Keep them producing.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat_budget = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors in village go to cave immediately (they will attack next step)
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining_farmers = list(farmers)
        MIN_FARMING = 2  # always keep at least 2 farmers farming for wheat production

        # Early game: spawn up to 2 farmers to grow economy
        if self.spawned_farmers < 2:
            while self.spawned_farmers < 2 and len(remaining_farmers) - 2 >= MIN_FARMING and wheat_budget >= 10:
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                wheat_budget -= 10
                self.spawned_farmers += 1

        # Aggressively spawn warriors to maintain a continuous attack pipeline
        # Use pairs of farmers + 12 wheat per warrior
        # Must leave MIN_FARMING farmers still farming
        while len(remaining_farmers) - 2 >= MIN_FARMING and wheat_budget >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            remaining_farmers = remaining_farmers[2:]
            wheat_budget -= 12

        # All remaining farmers farm to generate wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors deal 3 damage — always attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should never be in the cave; send them back
                environment.assign_group(c, "village")
```