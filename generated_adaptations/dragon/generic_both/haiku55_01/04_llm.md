## Analysis of the previous attempt

The 0% win rate has three likely causes:

1. **Too few warriors.** The Dragon has 50 HP and a warrior deals 3 damage per attack, so the fight needs about 17 warrior attacks. The old code capped spawning at two warriors ever, which is far too few.
2. **Spawning was throttled too much.** Only two spawn attempts per type were allowed, and farmers were held back unnecessarily, so wheat piled up unused.
3. **Warriors were lost to the Dragon's counterattacks.** Each attack round has a 40% chance of 1 damage to everyone in the Cave and a 20% chance of eating a villager. Warriors with 6 HP can only absorb a limited number of rounds, so the damage output has to come from a larger and continuously replenished warrior force.

## Revised strategy

The main change is to convert wheat into warriors as fast as possible, while keeping enough farmers to keep the wheat income going.

**In the Village (`assign_in_village`):**
- All warriors are sent to `"cave"` every step, so they never sit idle in the Village.
- A small number of farmers stay on `"farm"` to produce wheat. This reserve is 2 farmers when there are at least 4 farmers, and 1 otherwise.
- The remaining farmers are grouped into pairs. Each pair goes to `"spawn warrior"` while there is at least 12 wheat, so warrior production is limited only by wheat and farmer count, with no fixed attempt cap.
- If the farmer population drops below 4 and wheat remains after warrior spawning, one pair is sent to `"spawn farmer"` to rebuild the economy. This is also not capped.
- Every component is assigned on every step, because an unassigned component does not keep its previous group.

**In the Cave (`assign_in_cave`):**
- All warriors attack the Dragon every step. This ensures early damage, and the first attack happens well within the first 15 steps.
- Farmers that end up in the Cave are sent back to `"village"`.

**Trade-offs:** Spawning warriors early means fewer farmers are working the farm, so the wheat income drops. This is a deliberate choice, because the win condition depends on damage output within 30 steps, not on long-term economy.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Aggressive warrior-focused strategy.
    - All warriors go to the Cave and attack the Dragon every step.
    - Farmers stay on the farm, except that as many pairs as wheat allows are
      sent to 'spawn warrior' to maximise the damage output quickly.
    - A farmer pair is spawned when the farmer population gets too low.
    - Any farmer that ends up in the Cave is sent back to the Village.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LOW_FARMER_THRESHOLD = 4   # rebuild farmers if we drop below this
    MIN_FARMERS_FARMING = 2    # keep some wheat income

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reserve farmers that keep farming for wheat income.
        reserve = self.MIN_FARMERS_FARMING if len(farmers) >= 4 else 1
        reserve = min(reserve, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Prefer warriors: consume wheat in pairs while possible.
        while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # If the farmer population is low, rebuild it with leftover pairs.
        if len(farmers) < self.LOW_FARMER_THRESHOLD:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Anyone left over keeps farming.
        farming.extend(available)

        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers do not fight; send them back to the Village.
                environment.assign_group(c, "village")
```