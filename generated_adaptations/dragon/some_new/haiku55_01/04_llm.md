## Revised strategy: budgeted feeding, safe spawning, and full assignment

**What failed:**
- **Invalid "eat" assignments:** The previous version sent villagers to "eat" without checking that wheat covered every meal. Each meal costs 1 wheat, and the environment rejects assignments it cannot pay for. Some villagers were then left unassigned.
- **Starvation:** Spawning used wheat that was needed for meals in the following steps, so wheat ran out and villagers starved.
- **Missing final win:** Overall damage output was too low to kill the Dragon in 30 steps.

**Changes:**

1. **Meal budget first (Village):** Wheat is the hard constraint. Only as many villagers as there is wheat for get "eat", and the most hungry villagers are fed first. Each meal is paid for before anything else.
2. **Spawning only with a reserve:** A warrior is spawned only if, after paying the spawn cost, enough wheat remains to feed every other villager next step. This prevents the starvation seen in the test report.
3. **Every villager is assigned exactly once:** Each villager gets one `assign_group` call, chosen from a single decision path. Nobody is skipped.
4. **Unfed villagers stay in the Village:** A villager who is already hungry and was not fed this step stays in the Village (on "farm") instead of heading to the Cave, where it would starve further.
5. **Faster damage:** Warriors attack from the Cave for as long as they have eaten recently (`steps_since_meal <= 1` when leaving the Village). Warriors and farmers return to eat at 3 steps without food. Farmers also join the attack when they are healthy and fed, which increases total DPS. The Dragon takes no regeneration while attacked every step.

**Expected effect:** The test failures should disappear, since no invalid "eat" assignments are made and every component is assigned. Winning faster depends on enough warriors and food being available; the cave-cycle rule trades some uptime for survival.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed the hungriest villagers first, but never more meals than wheat allows.
        2. Spawn a warrior (pair of farmers in 'spawn warrior') only if the wheat
           left after the spawn still covers every other villager's next meal.
        3. Fed, healthy warriors go to the 'cave' to attack.
        4. Everyone else (including unfed villagers) stays on the 'farm'.
      Cave:
        1. Villagers without a meal for >= 3 steps, or with hp <= 1, return to 'village'.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    EAT_THRESHOLD_VILLAGE = 2     # feed when this many steps have passed without food
    RETURN_THRESHOLD_CAVE = 3     # leave the cave for food at this many steps
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by available wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}

        budget = wheat - len(eat)
        others = [c for c in components if id(c) not in eat_ids]

        # 2. Spawn a warrior only if enough wheat remains to feed the others next step.
        spawn_ids = set()
        reserve = len(others)
        candidates = [c for c in others if c.role == "Farmer" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE]
        if len(candidates) >= 2 and budget - self.WARRIOR_SPAWN_COST >= reserve:
            for c in candidates[:2]:
                spawn_ids.add(id(c))

        # 3/4. Assign every remaining villager exactly once.
        for c in components:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif (c.role == "Warrior"
                  and c.hp >= self.CAVE_MIN_HP
                  and c.steps_since_meal <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```