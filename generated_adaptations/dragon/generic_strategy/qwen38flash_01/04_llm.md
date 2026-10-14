

## Analysis and Improved Strategy

Looking at the 33% win rate, the main issues with the previous strategy are:

1. **Only spawning 2 warriors** - far too few to deal 50 damage before the 30-step limit and before the dragon kills them.
2. **Not spawning enough farmers** to sustain wheat production for more warriors.
3. **Not being aggressive enough** with spawning - we should keep spawning warriors as long as resources allow.

**New strategy:**
- **Spawn aggressively**: Don't cap at 2 warriors. Spawn warriors every round if we have ≥3 farmers (keep 1 farming) and ≥12 wheat. After getting 2+ warriors, also spawn farmers to maintain production.
- **Warriors always attack** in cave, never retreat.
- **Farmers never go to cave** - they farm or spawn in village.
- **Prioritize warrior spawning** over farmer spawning since warriors deal 3x more damage.
- **Track actual counts** by counting components rather than relying on counters that may not match reality.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Count current warriors (including the ones we just sent to cave)
        current_warriors = len(warriors)
        current_farmers = len(farmers)

        # Assign farmers: aggressive spawning strategy
        available_farmers = list(farmers)
        spawned_this_step_w = 0
        spawned_this_step_f = 0

        # Spawn warriors aggressively - keep at least 1 farmer farming
        # We want more than 2 warriors for fast dragon kill
        while len(available_farmers) >= 3 and wheat >= 12 and (current_warriors + spawned_this_step_w) < 8:
            parent1 = available_farmers.pop(0)
            parent2 = available_farmers.pop(0)
            environment.assign_group(parent1, "spawn warrior")
            environment.assign_group(parent2, "spawn warrior")
            wheat -= 12
            spawned_this_step_w += 1

        # Then spawn farmers to maintain production - keep at least 1 farming
        while len(available_farmers) >= 3 and wheat >= 10 and (current_farmers - 2 * spawned_this_step_w - 2 * spawned_this_step_f + spawned_this_step_f) >= 2:
            parent1 = available_farmers.pop(0)
            parent2 = available_farmers.pop(0)
            environment.assign_group(parent1, "spawn farmer")
            environment.assign_group(parent2, "spawn farmer")
            wheat -= 10
            spawned_this_step_f += 1

        # All remaining farmers go to farm
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers should not be in cave - send back to village
                environment.assign_group(c, "village")
```