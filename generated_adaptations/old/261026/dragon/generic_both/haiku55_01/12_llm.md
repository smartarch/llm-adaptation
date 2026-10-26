## Analysis of the previous attempt

Every version so far has scored 0%, and the last few also broke the task's explicit functional requirements:

1. **Warriors were held back on the farm.** The previous version kept warriors in the Village to build up. That violates "All warriors should go to the Cave" and risks the requirement to attack in the first 15 steps.
2. **Farmers were sent to fight.** The final-push rule sent farmers into the Cave. That violates "All farmers should stay in the Village."
3. **The Dragon has to take about 17 warrior hits in 30 steps.** Every warrior that is not attacking is wasted damage, so warriors need to be in the Cave from the start.

## Revised strategy: comply strictly, and maximise warrior output

The requirements are treated as hard constraints, and the economy is used to feed warrior production.

**In the Village (`assign_in_village`):**
- **Warriors** go to `"cave"` on every step, starting immediately, so they attack from the first step onward.
- **Farmers** never leave the Village.
  - Two farmers always stay on `"farm"` to keep wheat flowing.
  - If the farmer count is below 2 in total, all farmers stay on `"farm"` and no spawning happens.
  - Otherwise, the remaining farmers are paired. Each pair goes to `"spawn warrior"` while wheat is at least 12, which maximises damage output.
  - If the farmer count drops below 4, one pair goes to `"spawn farmer"` instead (10 wheat) to rebuild the economy and maintain a steady wheat income.

**In the Cave (`assign_in_cave`):**
- All warriors attack every step.
- Any farmer that somehow ends up in the Cave is sent back to `"village"`, so the farmer rule holds.

**Why this should help:** Warriors deal three times the damage of farmers, and they are in the Cave from the first step. Spawning is limited only by wheat and farmer count, so the army grows as fast as the economy allows, while the strategy stays within the task's constraints.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strictly rule-compliant, damage-focused strategy.
    - All warriors go to the Cave immediately and attack every step.
    - Farmers never enter the Cave. Two farmers always keep farming for wheat.
    - Remaining farmers are paired and spawn warriors whenever wheat allows.
    - If the farmer population falls below 4, pairs spawn farmers instead
      to rebuild the wheat economy.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMING = 2
    MIN_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors head straight to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Always keep a minimal farming core.
        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Rebuild the farmer economy if too few farmers remain.
        if len(farmers) < self.MIN_FARMERS:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Convert the remaining farmers into warriors while wheat allows.
        while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Anyone left over keeps farming.
        farming.extend(available)

        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers never fight; send them back to the Village.
                environment.assign_group(c, "village")
```