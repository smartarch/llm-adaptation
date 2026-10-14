## Analysis of the previous attempt

The strategy still never kills the Dragon, so the bottleneck is probably total damage output within 30 steps, not the way groups are split. Three factors matter:

1. **Damage needed:** The Dragon has 50 HP, so the fight needs about 17 warrior-attacks (3 damage each). The total number of warrior-rounds in the Cave is what limits the fight. Fewer rounds also means fewer Dragon counterattacks, because each round carries a 20% chance of losing a villager.
2. **Warrior count matters most:** Warriors deal 3 damage per attack versus 1 for farmers, and the wheat cost of a warrior (12) buys 3 times the damage of a farmer (10 wheat). Converting wheat into warriors is the fastest route to damage.
3. **Farmers are underused in the fight:** The previous code kept all farmers out of combat. In the final stretch, farmers add real damage, and a low Dragon HP means the economy no longer matters.

## Revised strategy

**In the Village (`assign_in_village`):**
- All warriors go to `"cave"` every step.
- Only **one** farmer stays on `"farm"` as a wheat source. Reserving two farmers slowed warrior production.
- The remaining farmers are paired and sent to `"spawn warrior"` while wheat allows (12 per pair). This is uncapped, so production is limited only by wheat and farmer count.
- If the farmer population falls below 3, leftover pairs are used for `"spawn farmer"` (10 wheat per pair) to rebuild the economy.
- Every component is assigned every step, because an unassigned component does not keep its previous group.

**In the Cave (`assign_in_cave`):**
- All warriors attack every step.
- Farmers also attack when the Dragon is at 15 HP or less (the final push). Before that, they go back to `"village"` to keep the wheat economy running.

**Trade-off:** Lower farming means less long-term wheat, but the win condition is decided within 30 steps, so converting wheat into damage quickly is the better bet.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Damage-maximising strategy.
    - All warriors go to the Cave and attack every step.
    - One farmer keeps farming for wheat; the rest are paired and spawn
      warriors whenever wheat allows (warriors give 3x the damage per wheat).
    - Farmers are rebuilt if the farmer population gets too small.
    - Farmers join the attack only in the final push (Dragon HP <= 15).
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LOW_FARMER_THRESHOLD = 3   # rebuild farmers if fewer than this
    FARMERS_KEPT_FARMING = 1   # minimal wheat income
    FINAL_PUSH_HP = 15         # farmers join the fight below this Dragon HP

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Keep a minimal farming reserve.
        reserve = min(self.FARMERS_KEPT_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Prefer warriors: spend wheat on pairs of farmers.
        while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Rebuild farmers if the population is too small.
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
        dragon_hp = environment.dragon.hp
        final_push = dragon_hp <= self.FINAL_PUSH_HP

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif final_push:
                # Farmers join the attack to finish the Dragon faster.
                environment.assign_group(c, "attack")
            else:
                # Farmers stay out of the fight until the final push.
                environment.assign_group(c, "village")
```