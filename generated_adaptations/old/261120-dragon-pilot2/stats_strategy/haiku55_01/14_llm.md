## Diagnosis of the last run

The win rate rose to 67%, and spawning is working: about 8 warriors per game, with wheat kept for meals. The remaining bottleneck is attack uptime. There are only 1.4 attackers per step, and the Dragon went unattacked for 3.7 steps, so it regenerates 5 HP on those steps. Warriors leave the Cave at 4 steps without food, so each one spends roughly 20% of its time walking and eating.

## Changes

1. **Longer Cave stay.** Warriors attack until `steps_since_meal` reaches 5, up from 4. A warrior that leaves at 5 reaches the Village at 6 and eats there, so its starvation window is exceeded for at most one step. This is a small risk, and it is the only change that raises attack uptime without new mechanics.
2. **Eating priority at the threshold.** Warriors that have reached the leave threshold are sorted first in the meal queue, so when wheat is short, the warriors that need food most eat first.
3. **Spawning unchanged.** Greedy warrior spawning from idle farmer pairs works well, so it stays as is.
4. **Farmers stay in the Village** and never enter the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors attack in the Cave while steps_since_meal < 5, then walk back and eat.
      Freshly fed warriors (steps_since_meal == 0) go straight back to the Cave.
    - Every step, idle farmers are paired into "spawn warrior" groups while wheat above
      a small meal reserve covers 12 wheat per pair.
    - Meals are assigned first, most hungry first, so no one starves for lack of food.
    - Farmers not eating or spawning farm wheat; they never enter the Cave.
    """

    WARRIOR_LEAVE_CAVE_AT = 5
    FARMER_EAT_AT = 3
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals: warriors that are not freshly fed, farmers at the threshold.
        #    If wheat is short, the most hungry villagers eat first.
        candidates = [c for c in warriors if c.steps_since_meal >= 1]
        candidates += [c for c in farmers if c.steps_since_meal >= self.FARMER_EAT_AT]
        candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        eaters = candidates[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Small wheat reserve for the next step's meals.
        reserve = len(warriors) // 2 + 1

        # 3) Greedy warrior spawning from pairs of idle farmers.
        spawn_ids = set()
        pool = list(idle_farmers)
        while len(pool) >= 2 and wheat - reserve >= self.WARRIOR_COST:
            pair = pool[:2]
            pool = pool[2:]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 4) Fresh warriors go to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 5) Remaining farmers farm.
        for c in idle_farmers:
            if id(c) not in spawn_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```