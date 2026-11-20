## Revised Strategy: Longer Early Farmer Phase

The last change (spawn cap 2 to 3) kept the 100% win rate but did not reduce the 25-step win time, so the cap is not the bottleneck. The limit seems to be economy: Warriors can only be spawned as fast as wheat comes in, and Farmers are the only units that produce much of it (5 wheat each, versus 2 for Warriors).

This version changes one parameter. `EARLY_FARMER_STEPS` goes from 8 to 12, so extra Farmer pairs are spawned when no Warrior is affordable for a longer stretch of the game.

**Reasoning**
- Each Farmer adds 5 wheat per step while farming. Extra Farmers therefore raise the wheat available for Warrior spawns (12 each) and meals later in the game.
- Early Farmer spawns only happen on steps where no Warrior is affordable, so they do not delay Warrior spawns that wheat already supports.
- Meals are still paid first, so starvation risk does not change.

**What to watch**
- This is a hypothesis, not a measured result. The win time may stay at 25 or move either way.
- If the win rate drops, revert to `EARLY_FARMER_STEPS = 8`. The Farmer pairs spent on spawns come off the farm for one step each, so too many of them can cost wheat.
- Test this version several times before comparing it with the previous one.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with a longer early economy phase (single-parameter change):
      - Villagers eat at 3 steps without a meal, paid from a running wheat budget.
      - Warrior spawns from Farmer pairs, up to three spawns per step.
      - Early Farmer spawns in the first 12 steps when no Warrior is affordable (was 8).
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm.
    """

    EAT_THRESHOLD = 3
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 3
    EARLY_FARMER_STEPS = 12     # changed from 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        # 1) Meals first: anyone close to starving eats (1 wheat each)
        eaters = []
        rest = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []
        spawn_farmer = []

        # 2) Warrior surge, capped at MAX_SPAWNS_PER_STEP spawns per step
        spawns = 0
        if dragon_alive:
            while (spawns < self.MAX_SPAWNS_PER_STEP
                   and len(free_farmers) >= 2 and budget >= self.WARRIOR_COST):
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                budget -= self.WARRIOR_COST
                spawns += 1

        # 3) Early economy: one Farmer pair if no Warrior was spawned this step
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.FARMER_COST):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Free Warriors head to the Cave; everyone else farms
        to_cave = list(free_warriors) if dragon_alive else []
        farming = free_farmers + ([] if dragon_alive else free_warriors)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farming:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Farmers go home to farm; Warriors go home when a meal is due
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```