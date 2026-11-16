## Revised Strategy: Extend the Early Farmer Phase Further

The last change (`EARLY_FARMER_STEPS` from 8 to 12) kept the 100% win rate and cut the average win time from 25.0 to 24.7. That suggests more Farmer production early on helps a little. This version continues the same direction with one change: `EARLY_FARMER_STEPS` goes from 12 to 16.

**Reasoning**
- Farmers are the main wheat producers (5 wheat per step, versus 2 for Warriors). Extra Farmers early raise the wheat available for later Warrior spawns and meals.
- Early Farmer spawns still happen only on steps where no Warrior is affordable, so they do not displace Warrior spawns that wheat already supports.
- Meals are still paid first, so starvation risk is unchanged.

**What to watch**
- The gain from 8 to 12 was small (0.3 steps), so this change may be too small to see in a few runs. Test it over many games before comparing.
- If the win rate drops or the win time rises, revert to `EARLY_FARMER_STEPS = 12`. Each early Farmer pair is taken off the farm for a step, and too many of them can cost wheat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with a longer early economy phase (single-parameter change):
      - Villagers eat at 3 steps without a meal, paid from a running wheat budget.
      - Warrior spawns from Farmer pairs, up to three spawns per step.
      - Early Farmer spawns in the first 16 steps when no Warrior is affordable (was 12).
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm.
    """

    EAT_THRESHOLD = 3
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 3
    EARLY_FARMER_STEPS = 16     # changed from 12

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