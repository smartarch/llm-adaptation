Strategy update (new approach)

- Goal
  - Increase the chance to kill the Dragon sooner by getting Warriors into the Cave and attacking as early as possible, while still maintaining wheat production to enable spawns.
  - Preserve the rule that every component is assigned exactly once per step.
  - Use a simple, predictable spawning policy that favors early Warrior spawns, since Warriors deal more damage to the Dragon.

- Key changes from the previous version
  - In assign_in_village, after the initial early farming window (steps 1-3), spawn Warriors first as long as there is enough wheat and enough Farmers available. Only then spawn Farmers. This prioritizes DPS earlier, which can reduce the number of steps needed to bring the Dragon HP to zero.
  - Farmers are still used to farm when not spawning, ensuring wheat production continues.
  - All Warriors are still moved to the Cave in assign_in_village and attack in assign_in_cave, keeping behavior consistent with the rules.

- Why this should improve win rate
  - Faster buildup of Warriors means higher DPS on the Dragon earlier, increasing the probability of killing it within 30 steps.
  - Early farming remains to sustain future spawns, but the policy shifts some riskier spawning toward Warriors to boost early damage.

Updated Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all existing warriors to the cave (to travel to Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Early steps: focus on farming to accumulate wheat
        if step <= 3 or len(farmers) == 0:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Strategy: spawn Warriors first (if possible), then spawn Farmers
        leftover_farmers = len(farmers)
        leftover_wheat = wheat
        w_spawns = 0
        f_spawns = 0

        # Spawn as many Warriors as possible: needs 2 farmers and 12 wheat per spawn
        while leftover_farmers >= 2 and leftover_wheat >= 12:
            w_spawns += 1
            leftover_farmers -= 2
            leftover_wheat -= 12

        # Then spawn as many Farmers as possible with remaining resources
        while leftover_farmers >= 2 and leftover_wheat >= 10:
            f_spawns += 1
            leftover_farmers -= 2
            leftover_wheat -= 10

        # Assign each farmer to exactly one group in a single pass
        # First 2*w_spawns farmers -> "spawn warrior"
        # Next 2*f_spawns farmers -> "spawn farmer"
        # Remaining farmers -> "farm"
        for idx, f in enumerate(farmers):
            if idx < 2 * w_spawns:
                environment.assign_group(f, "spawn warrior")
            elif idx < 2 * w_spawns + 2 * f_spawns:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack with warriors; farmers go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```