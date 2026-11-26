## Diagnosis

The failing tests show three problems:

1. **Wheat reserve was too thin.** The strategy spent wheat on spawning and left too little for the meals due in the next step, so villagers starved (Maria at step 23).
2. **The Dragon was not killed in time.** Warriors were held back by the launch-group threshold and spawning was too slow, so the damage arrived too late, near step 30.
3. **Spawning was gated by an unclear wheat calculation.** It did not reliably produce new warriors.

## Revised strategy

**Village**
- **Eat:** villagers with `steps_since_meal >= 2` eat, most-hungry first, as long as wheat lasts. This keeps everyone far from the 6-step starvation limit.
- **Reserve wheat:** before spending on anything else, keep one wheat per villager (the meals due after this step). Only wheat above this reserve is available for spawning.
- **Spawn warriors:** pairs of idle farmers go to "spawn warrior" while the surplus covers 12 wheat per warrior. Warriors deal 3 damage against 1 for farmers, so warriors are the best use of wheat.
- **Launch:** every healthy, freshly fed warrior (hp ≥ 3, `steps_since_meal < 2`) goes to the Cave. There is no minimum group size, because the Dragon regenerates 5 HP per step without attacks, and each attack step counts.
- **Farm:** everyone else farms, which produces the wheat for meals and spawning.

**Cave**
- Warriors attack while `steps_since_meal < 4` and `hp >= 2`.
- Hungry or badly wounded warriors return to the Village. The 4-step cutoff leaves enough margin for the return step and the meal.
- Farmers never fight, so any farmer in the Cave returns to farming.

Because warriors rotate between the Cave and the Village, some warrior is usually attacking each step, so the Dragon rarely regenerates.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers with steps_since_meal >= 2 while keeping one
        wheat per villager in reserve for the meals due next step. Spare wheat
        spawns new warriors from pairs of idle farmers. Fresh, healthy warriors
        are sent to the Cave immediately. Everyone else farms.
      - Cave: warriors attack every step while fed and healthy, so the Dragon
        is hit almost continuously and never gets to regenerate. Hungry or
        badly wounded warriors return to the Village. Farmers never fight.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat early, well before the 6-step limit
    RETREAT_THRESHOLD = 4       # leave the Cave when hunger reaches this
    MIN_WARRIOR_HP_LAUNCH = 3   # warriors below this stay home
    MIN_WARRIOR_HP_CAVE = 2     # warriors below this retreat from the Cave
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1. Eating: feed hungry villagers, most hungry first.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1
        wheat_after_meals = eat_budget

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Reserve: one wheat per villager for the meals due next step.
        reserve = len(components)
        spare = wheat_after_meals - reserve

        # 3. Spawning: pairs of idle farmers become a new warrior when the
        #    surplus covers the cost.
        farmers_idle = [c for c in remaining if c.role == "Farmer"]
        if dragon_alive:
            while len(farmers_idle) >= 2 and spare >= self.WARRIOR_COST:
                assign(farmers_idle.pop(0), "spawn warrior")
                assign(farmers_idle.pop(0), "spawn warrior")
                spare -= self.WARRIOR_COST

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Launch: every fresh, healthy warrior goes to the Cave.
        if dragon_alive:
            for c in remaining:
                if (c.role == "Warrior"
                        and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
                        and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE):
                    assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 5. Everyone else farms.
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if c.role == "Farmer":
                # Farmers do not fight; send them back to farm.
                environment.assign_group(c, "village")
            elif not dragon_alive:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal >= self.RETREAT_THRESHOLD or c.hp < self.MIN_WARRIOR_HP_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```