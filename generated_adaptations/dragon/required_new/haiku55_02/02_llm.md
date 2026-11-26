## Strategy: all-in warrior assault with rotating meals

**Goal:** Kill the 100 HP Dragon within 30 steps while keeping every villager fed.

**Key observations:**
- Only villagers in the Cave deal damage, and warriors deal 3 damage versus 1 for farmers. The Dragon regenerates 5 HP per step only when nobody attacks, so the cave should be attacked on every step.
- Farmers produce the wheat needed for meals and spawning, so they stay on the farm.
- Villagers can't eat in the Cave, and they starve after 6 steps without a meal. Cave warriors therefore rotate out to eat before they reach the danger zone.

**Rules implemented:**

*In the Village:*
1. Any villager with `steps_since_meal >= 3` goes to "eat". This is a safety margin below the 6-step starvation limit.
2. Early on (step ≤ 15), if wheat is at least 16 (12 for a warrior plus a reserve for meals) and two fed farmers are available, those two farmers go to "spawn warrior". Spawned warriors add damage for the rest of the fight.
3. Remaining healthy warriors (`hp >= 3`) go to "cave".
4. All other villagers, mainly farmers, go to "farm".

*In the Cave:*
1. Warriors that are starving soon (`steps_since_meal >= 3`) or low on HP (`hp <= 2`) go back to "village" to eat or recover.
2. All other villagers go to "attack".

The rotation keeps most warriors attacking each step, which minimizes Dragon regeneration. The margin of 3 steps means that a warrior returning for a meal (one step of travel, one step of eating, and one step back) stays well inside the starvation window.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors do the fighting in the Cave; they attack every step to minimize
      Dragon regeneration.
    - Farmers stay in the Village to produce wheat (needed for meals and spawns).
    - Any villager that has gone 3+ steps without eating is sent to eat in the
      Village (safety margin below the 6-step starvation limit).
    - Early on, when wheat allows, two farmers are used to spawn an extra warrior.
    - In the Cave, villagers that are hungry or badly hurt are sent back to the
      Village; everyone else attacks.
    """

    HUNGER_THRESHOLD = 3      # eat when this many steps without a meal
    SPAWN_STEP_LIMIT = 15     # only spawn early enough to matter
    SPAWN_WHEAT_RESERVE = 4   # keep some wheat for meals after spawning
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_HP_IN_CAVE = 2

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        remaining = list(components)

        # 1) Hungry villagers must eat now.
        hungry = [c for c in remaining if c.steps_since_meal >= self.HUNGER_THRESHOLD]
        for c in hungry:
            environment.assign_group(c, "eat")
            wheat -= 1  # each meal consumes 1 wheat
        ready = [c for c in remaining if c not in hungry]

        # 2) Optionally spawn a warrior early in the fight (needs 2 farmers + wheat).
        spawn_pair = []
        if step <= self.SPAWN_STEP_LIMIT and wheat >= self.WARRIOR_SPAWN_COST + self.SPAWN_WHEAT_RESERVE:
            farmers_ready = [c for c in ready if c.role == "Farmer"]
            if len(farmers_ready) >= 2:
                spawn_pair = farmers_ready[:2]
                for c in spawn_pair:
                    environment.assign_group(c, "spawn warrior")
                wheat -= self.WARRIOR_SPAWN_COST
        ready = [c for c in ready if c not in spawn_pair]

        # 3) Healthy warriors go fight; everyone else farms.
        for c in ready:
            if c.role == "Warrior" and c.hp >= self.MIN_WARRIOR_HP_FOR_CAVE:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.HUNGER_THRESHOLD or c.hp <= self.MIN_HP_IN_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```