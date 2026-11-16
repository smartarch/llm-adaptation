## Diagnosis of the last run

The win rate rose to 33%, and warriors spawned well (8.7 per game), but the Dragon still survived with 18 HP on average. Only 1.2 villagers attacked per step, and the Dragon went unattacked for 5.3 steps. The bottleneck is attack uptime. Warriors leave the Cave at 3 steps without food, so each one spends roughly a quarter of its time away. Many steps therefore have only one or two attackers.

## Key observations

- Spawning takes villagers from the group only for the step. They are not consumed, so pairing farmers into "spawn warrior" every step is nearly free apart from wheat.
- The Dragon's counterattacks hit everyone in the Cave, and the 20% "eat one" event picks a random villager. More warriors in the Cave does not raise the per-step death rate, so it is better to have more attackers.
- Starvation occurs at 6 consecutive steps without eating. A warrior that leaves the Cave at 4 steps, walks for one step, and eats on arrival stays safely under the limit.

## Revised strategy

1. **Longer warrior stay.** Warriors attack while `steps_since_meal < 4` (up from 3). The walk plus meal still keeps them under the starvation limit.
2. **Immediate return.** A warrior in the Village with `steps_since_meal >= 1` eats. A warrior that has just eaten (counter 0) goes straight back to the Cave, so it is never idle in the Village.
3. **Greedy warrior spawning.** Every step, every pair of idle farmers becomes a "spawn warrior" group while wheat above a small meal reserve is at least 12. The reserve is `warriors // 2 + 1`, which covers the expected meals of the next step.
4. **Hungriest-first feeding.** If wheat runs short, the most hungry villagers eat first.
5. **Farmers stay in the Village** and never enter the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors attack in the Cave while steps_since_meal < 4, then walk back, eat, and return.
      Fresh warriors (just fed) go straight back to the Cave.
    - Every step, idle farmers are paired into "spawn warrior" groups as long as wheat above
      a meal reserve covers 12 wheat per pair. Spawning does not consume the farmers.
    - Meals are assigned first, most hungry first, so no one starves for lack of food.
    - Farmers that are not eating or spawning farm wheat. They never enter the Cave.
    """

    WARRIOR_LEAVE_CAVE_AT = 4
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

        # 2) Keep a small wheat reserve for the next step's meals.
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