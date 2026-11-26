## Revised strategy: longer cave shifts and a damage-first spawn policy

**What the report shows:**
- All per-step validity and required checks pass. Starvation, invalid assignments, and unassigned villagers are no longer a problem.
- The only failures are the end-of-game checks: the Dragon is not killed within 30 steps. The 33% win rate and 29-step average confirm that the team is too slow, not unsafe.

**Diagnosis:**
- **Short cave shifts waste attacks.** Warriors returned to the village at `steps_since_meal >= 3`, so each cycle gave only about two attacking steps. The Dragon regenerates 5 HP whenever it is not attacked, so these gaps cost real progress.
- **Damage is the bottleneck.** About 34 warrior attacks are needed. The fastest path is more warriors attacking on more steps.

**Changes:**

1. **Longer cave shifts.** Warriors stay in the cave until `steps_since_meal >= 4` (previously 3). A warrior that eats in the village then needs one step to return, so it arrives with a counter of 5 and is fed before reaching 6. The village feeding rule is unchanged, and wheat still covers every meal first.
2. **Earlier safety retreat.** Warriors leave the cave at `hp <= 2` rather than `hp <= 1`. A 40% Dragon attack deals 1 damage to everyone in the cave, so a warrior at 2 HP could die in one attack.
3. **Warriors re-enter immediately after eating.** Any warrior fed recently (`steps_since_meal <= 1`) and healthy goes straight back to the cave.
4. **Damage-first spawning.** Free farmer pairs are turned into warriors whenever the wheat left after the spawn covers the next step's meals. The farm-income term is dropped from the check. Farming income is still counted by the stock check, and at least one farmer keeps working when wheat is low.
5. **Every villager is assigned exactly once** in each call.

**Expected effect:** Warriors attack for about 4 of every 5 steps instead of about 2 of 3, and more warriors appear sooner. Total damage should reach 100 within 30 steps, while feeding rules keep villagers alive.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (steps_since_meal >= 2), limited by wheat.
        2. Spawn warriors from free farmer pairs while the wheat left after the
           spawn covers the meals needed next step; keep one farmer working when
           wheat is low.
        3. Healthy warriors that ate recently go to the cave to attack.
        4. Everyone else stays on the farm.
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

        # 2. Spawn warriors from free farmer pairs.
        spawn_ids = set()
        spawned = 0
        while len(free_farmers) - spawned >= 2:
            budget_after = budget - self.WARRIOR_SPAWN_COST
            if budget_after < needing_food:
                break
            farming_after = len(rest_farmers) - (spawned + 2)
            if farming_after == 0 and budget < self.LOW_WHEAT:
                break  # keep wheat income alive when the stock is low
            budget = budget_after
            for c in free_farmers[spawned:spawned + 2]:
                spawn_ids.add(id(c))
            spawned += 2

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