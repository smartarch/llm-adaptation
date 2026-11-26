## Strategy: Greedy Attack with Starvation Guard

**Goal:** Kill the Dragon (100 HP) within 30 steps while keeping every villager fed.

**Key observations:**
- Warriors deal 3 damage per attack and farmers deal 1, so warriors are the main damage source.
- The Dragon regenerates 5 HP per step only when nobody attacks, so the cave group should attack every step it can.
- Starvation begins after 6 steps without a meal, and starving villagers deal no damage. Villagers should eat well before that limit.
- Attacking is the only way to bring the Dragon down, so idle villagers in the cave are wasted damage.

**Village rules:**
1. **Eat:** Any villager with `steps_since_meal >= 3` goes to "eat" (if wheat is available). The margin of 3 leaves room for a one-step mismatch in the counter.
2. **Spawn:** Early in the fight (step ≤ 10), if there is enough wheat for a warrior (12) and at least two farmers are free, two farmers go to "spawn warrior". Warriors are the better attackers, so this trade is worth it while there is time to benefit.
3. **Cave:** Free warriors go to the cave to attack.
4. **Farm:** Free farmers stay on the farm to produce the wheat needed for food and spawning. Once wheat is plentiful (≥ 15), extra farmers join the cave to add damage.

**Cave rules:**
1. Villagers with `steps_since_meal >= 3` return to the village. They arrive, eat immediately, and reset their counter.
2. All other villagers are assigned to "attack" every step, which keeps the Dragon from regenerating.

**Assumptions:** The exact timing of counter resets is uncertain, so the thresholds are conservative. The farm-to-cave split is a heuristic and may need tuning.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Greedy adaptation:
      - Keep every villager fed (eat when steps_since_meal >= 3, a safety margin
        below the 6-step starvation limit).
      - Early on, spawn extra warriors (the strongest attackers) when wheat allows.
      - Send warriors to the cave; farmers keep farming for food unless wheat is plentiful.
      - In the cave, attack every step (so the Dragon never regenerates) and retreat
        villagers that are close to starving.
    """

    EAT_THRESHOLD_VILLAGE = 3
    EAT_THRESHOLD_CAVE = 3
    SPAWN_STEP_LIMIT = 10
    WARRIOR_SPAWN_COST = 12
    WHEAT_SURPLUS = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        remaining = []

        # 1) Feed anyone approaching the starvation limit.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                remaining.append(c)

        # 2) Spawn a warrior early in the fight if affordable (uses two farmers as inputs).
        farmers_free = [c for c in remaining if c.role == "Farmer"]
        spawned_inputs = set()
        if (step <= self.SPAWN_STEP_LIMIT
                and wheat >= self.WARRIOR_SPAWN_COST
                and len(farmers_free) >= 2):
            for c in farmers_free[:2]:
                environment.assign_group(c, "spawn warrior")
                spawned_inputs.add(id(c))
            wheat -= self.WARRIOR_SPAWN_COST

        # 3) Route the rest.
        for c in remaining:
            if id(c) in spawned_inputs:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:  # Farmer
                if wheat >= self.WHEAT_SURPLUS:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_CAVE:
                # Retreat to eat before starvation sets in.
                environment.assign_group(c, "village")
            else:
                # Keep attacking every step so the Dragon never regenerates.
                environment.assign_group(c, "attack")
```