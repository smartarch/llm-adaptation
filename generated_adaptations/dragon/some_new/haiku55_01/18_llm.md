## Revised strategy: projected wheat income for spawning

**What the report shows:**
- All validity, assignment, and per-step checks pass.
- The only failures are the end-of-game checks: the Dragon survives 30 steps in some runs. The win rate is 33%, and winning runs take 21 steps on average, so the team is still too slow to kill the Dragon in every run.

**Diagnosis:**
- Damage is the bottleneck. About 34 warrior attacks are needed, and each spawn adds 3 damage per step for the rest of the game.
- The spawn check ignores the wheat that farmers and resting warriors produce. It only compares the current stock with next step's meals. This makes it stricter than necessary, so spawns are delayed even when income would cover them.
- The `LOW_WHEAT` guard also blocks the last farmer pair from spawning when the stock is modest, even though that pair would produce a warrior that pays back quickly.

**Changes:**

1. **Projected-income spawn check.** A pair of farmers is spawned into a warrior when `wheat_after_spawn + income_next_step >= meals_next_step`. Income is 5 per farmer still farming and 2 per warrior still farming. Warriors in the cave produce nothing, so they are not counted.
2. **Removed the low-wheat block.** The projected check already guards against running out. The emergency spawn stays as a fallback when no warriors exist.
3. **Unchanged safety rules.** Hungry villagers are fed first, limited by wheat. Warriors cycle through the cave for 4 steps and go home at `hp <= 2`. Every villager is assigned exactly once per call.

**Expected effect:** Warriors should appear earlier, so more attacks land sooner. This is a tuning change, not a verified fix. The required end-of-game checks are the ones that still need to pass, so the change should be checked against the simulation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs while the projected wheat
           (stock after spawn + income from farmers and warriors still farming)
           covers the meals needed next step. If no warriors exist, spawn as
           soon as the stock allows.
        3. Healthy warriors that ate recently go to the cave to attack.
        4. Everyone else (including farmers) stays on the farm.
      Cave:
        1. Warriors that have not eaten for >= 4 steps, or have hp <= 2, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    HUNGRY_THRESHOLD = 2
    RETURN_THRESHOLD = 4
    CAVE_MIN_HP = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_INCOME = 5
    WARRIOR_INCOME = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.HUNGRY_THRESHOLD]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}
        budget = wheat - len(eat)

        rest = [c for c in components if id(c) not in eat_ids]
        rest_farmers = [c for c in rest if c.role == "Farmer"]
        free_farmers = [c for c in rest_farmers if c.steps_since_meal < self.HUNGRY_THRESHOLD]
        has_warrior = any(c.role == "Warrior" for c in components)

        # Villagers that will need food next step.
        needing_food = sum(1 for c in rest if c.steps_since_meal >= 1)

        # 2. Spawn warriors from free farmer pairs using projected income.
        spawn_ids = set()
        spawned = 0
        while len(free_farmers) - spawned >= 2:
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < 0:
                break

            # Income next step from villagers still farming after this spawn.
            farmers_after = [c for c in rest_farmers
                             if id(c) not in spawn_ids
                             and c not in free_farmers[spawned:spawned + 2]]
            warriors_farming = [c for c in rest
                                if c.role == "Warrior"
                                and id(c) not in spawn_ids]
            income = (self.FARMER_INCOME * len(farmers_after)
                      + self.WARRIOR_INCOME * len(warriors_farming))

            if has_warrior and budget_after + income < needing_food:
                break  # normal case: projected wheat cannot cover next step's meals

            budget = budget_after
            for c in free_farmers[spawned:spawned + 2]:
                spawn_ids.add(id(c))
            spawned += 2
            has_warrior = True

        # 3/4. Assign every villager exactly once.
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
            if c.steps_since_meal >= self.RETURN_THRESHOLD or c.hp <= 2:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```