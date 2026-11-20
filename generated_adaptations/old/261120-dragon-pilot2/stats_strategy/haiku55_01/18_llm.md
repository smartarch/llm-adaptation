## Diagnosis of the last run

The win rate was 67% with no starvation, and about 8 warriors spawned per game. Two inefficiencies remain:

1. **The wheat reserve is too blunt.** It is set to `warriors // 2 + 1` regardless of who actually needs food next step. That holds back wheat that could fund another warrior pair.
2. **Attack uptime is still about 1.4 per step.** Warriors that leave the Cave at count 4 are away for about two steps (walk, then eat), so the Dragon goes unattacked on some steps.

## Changes

1. **Exact meal forecast.** The reserve is the number of villagers who will have to eat on the next step: warriors at `steps_since_meal >= 3` and farmers at the farmer threshold. Only that wheat is kept back, so the rest can fund spawns.
2. **Staggered warrior return.** A warrior that has just eaten (count 0 in the Village) returns to the Cave immediately. A warrior that has been in the Cave for 4 steps leaves. Since spawns are added in pairs each step, new warriors refill the Cave quickly, so the rotation stays staggered.
3. **Early-game spawn priority.** In the first steps, the wheat budget goes to spawning warriors before any farmer is kept idle, so the damage pool grows as early as possible.
4. **Starvation safety unchanged.** Warriors leave at count 4, walk for one step, and eat on arrival at count 5, which is below the 6-step limit. Meals are still assigned most urgent first.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors attack in the Cave while steps_since_meal < 4, then walk back and eat on arrival
      (count 5, still below the starvation limit). Freshly fed warriors return to the Cave at once.
    - Meals are assigned first, most urgent first. The wheat reserve equals exactly the number of
      villagers who must eat next step (warriors at count >= 3, farmers at the farmer threshold).
    - All remaining wheat funds "spawn warrior" pairs from idle farmers.
    - Farmers never enter the Cave; they farm when not eating or spawning.
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
        #    Most urgent first, so that starvation is handled before anything else.
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

        # 3) Spawn warriors from pairs of idle farmers with the remaining wheat.
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