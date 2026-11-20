## Diagnosis of the last run

The win rate has held at 67% for several revisions, and the average win time has stayed around 22 to 25 steps. Two things limit the results:

1. **Wheat is spent on warriors only.** The economy never grows. Only 2 farmers remain, and each farmer yields 5 wheat per step, which caps how many warrior pairs can be funded later in the fight.
2. **Attack uptime is about 1.4 per step.** The Dragon regenerates on roughly 4 steps per game. Pushing warriors to stay longer risks starvation, which has already caused failures.

## Changes

1. **Early economy boost with farmers.** During the first 3 steps, if wheat above the meal reserve covers a farmer pair (10 wheat) and fewer than 5 farmers exist, idle farmers spawn a farmer instead of a warrior. Those farmers then produce wheat for the rest of the fight. The earlier attempt failed because of a minimum-farmer rule that blocked all spawning. That rule is removed here.
2. **Warrior spawning after the boost.** Once the boost window closes, every affordable pair of idle farmers spawns a warrior, as before.
3. **Exact meal reserve.** The reserve is the number of villagers who need to eat on the next step, so wheat is not held back unnecessarily.
4. **Safe cave cycle unchanged.** Warriors attack while `steps_since_meal < 4`. They walk back, eat on arrival at count 5, and return once fresh. Meals are still assigned most urgent first to avoid starvation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors attack in the Cave while steps_since_meal < 4, then walk back and eat on arrival
      (count 5, still below the starvation limit). Freshly fed warriors return to the Cave at once.
    - Meals are assigned first, most urgent first. The wheat reserve equals the number of
      villagers who must eat on the next step.
    - Early (first 3 steps), idle farmer pairs spawn farmers while the farmer count is small,
      to grow wheat income. After that, idle farmer pairs spawn warriors with all spare wheat.
    - Farmers never enter the Cave; they farm when not eating or spawning.
    """

    WARRIOR_LEAVE_CAVE_AT = 4
    FARMER_EAT_AT = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    ECONOMY_STEPS = 3
    MAX_FARMERS = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals: warriors that are not freshly fed, farmers at the threshold.
        #    Most urgent first, so starvation is handled before anything else.
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

        # 2) Exact reserve: villagers who will need a meal on the next step.
        reserve = sum(1 for c in warriors if c.steps_since_meal >= 3)
        reserve += sum(1 for c in farmers if c.steps_since_meal + 1 >= self.FARMER_EAT_AT)

        # 3) Spawning from pairs of idle farmers.
        spawn_ids = set()
        pool = list(idle_farmers)
        total_farmers = len(farmers)

        # Early economy boost: farmers spawn farmers while the farm is small.
        while (step < self.ECONOMY_STEPS and len(pool) >= 2
               and total_farmers < self.MAX_FARMERS
               and wheat - reserve >= self.FARMER_COST):
            pair = pool[:2]
            pool = pool[2:]
            for c in pair:
                environment.assign_group(c, "spawn farmer")
                spawn_ids.add(id(c))
            wheat -= self.FARMER_COST
            total_farmers += 0  # newborns appear next step; avoid double-counting

        # Main phase: warriors from pairs of idle farmers with the remaining wheat.
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