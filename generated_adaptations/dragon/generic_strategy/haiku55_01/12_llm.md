## Revised Strategy: Restore the 100% Version

My last "baseline" was not the version that scored 100%. I left out two features of the original: the early Farmer spawns (steps 0 to 7, when wheat allows) and the cap of two Warrior spawns per step. The 33% result shows that removing them hurt reliability. The earlier 100% result is the best measured outcome, so this version restores that code exactly.

The original design works because:
- **Early Farmer spawns** add producers while the Dragon is still healthy, which raises wheat income for later Warrior spawns and meals.
- **Meals are paid first** from a running wheat budget, so spawns never take the wheat needed to feed villagers who are due.
- **Warriors attack from the Cave** and return at 3 steps without a meal, which keeps them out of starvation.
- **Farmers stay in the Village** to farm and fund spawns.

I can't verify the 25-step figure without the simulator, and the win rate varies between runs, so the next step is to test this version several times before changing anything else. Any speed change should be tested alone, so its effect on reliability is visible.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge with early economy (the version that achieved 100% in testing):
      - Villagers eat at 3 steps without a meal, paid from a running wheat budget.
      - Warrior spawns from Farmer pairs, at most two spawns per step.
      - Early Farmer spawns in the first steps when no Warrior is affordable.
      - Warriors attack in the Cave and return at 3 steps without a meal.
      - Farmers stay in the Village to farm.
    """

    EAT_THRESHOLD = 3
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 2
    EARLY_FARMER_STEPS = 8

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

        # 2) Warrior surge, capped at two spawns per step
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