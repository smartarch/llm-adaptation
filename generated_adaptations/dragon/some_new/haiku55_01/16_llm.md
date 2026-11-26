## Revised strategy: revert farmer attacks and add an emergency warrior spawn

**What the report shows:**
- All validity, assignment, and per-step required checks pass.
- The win rate dropped from 33% to 0% after farmers started attacking. Farmers have only 4 HP, so the Dragon's attacks kill them quickly. Sending them to the cave also removes wheat income, which leads to fewer fed villagers and fewer spawns.
- The optional hints show that the team sometimes has no warriors for several steps. Nobody attacks during those steps, and the Dragon regenerates.

**Changes:**

1. **Farmer attacks removed.** Farmers stay on the farm. This protects wheat income and avoids losing 4-HP farmers to the Dragon's attacks.
2. **Emergency warrior spawn.** When no warriors remain, the spawn rule only requires that the wheat after the spawn is non-negative, not that it covers the next step's meals. A warrior is the only source of damage, so a short-term hunger risk is accepted. Normal spawns still reserve wheat for next step's meals.
3. **Warrior cycle unchanged.** Warriors leave the cave at `steps_since_meal >= 4` or `hp <= 2`, and re-enter as soon as they have eaten. This gave the best observed win rate so far.
4. **Every villager is assigned exactly once** in each call.

**Expected effect:** The team returns to the configuration that reached a 33% win rate, and the emergency spawn closes the gaps where no warriors are present.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs while the wheat left after the
           spawn covers the meals needed next step. If no warriors exist, spawn
           as soon as the wheat allows. Keep one farmer working when wheat is low.
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
    LOW_WHEAT = 10

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

        # Villagers that will need food next step.
        needing_food = sum(1 for c in rest if c.steps_since_meal >= 1)
        has_warrior = any(c.role == "Warrior" for c in components)

        # 2. Spawn warriors from free farmer pairs.
        spawn_ids = set()
        spawned = 0
        while len(free_farmers) - spawned >= 2:
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < 0:
                break
            if has_warrior and budget_after < needing_food:
                break  # normal case: keep wheat for next step's meals
            farming_after = len(rest_farmers) - (spawned + 2)
            if farming_after == 0 and budget < self.LOW_WHEAT and has_warrior:
                break  # keep wheat income alive when the stock is low
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