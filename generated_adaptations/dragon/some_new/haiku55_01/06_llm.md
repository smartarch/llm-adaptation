## Revised strategy: faster warrior growth and more uptime

**What the report shows:** All per-step validity tests pass now. The only remaining failures are the end-of-game checks: the Dragon is not killed within 30 steps. The game is a damage race, so the fix is more sustained DPS, not safer feeding.

**Diagnosis:**
- Total damage was too low. 100 HP needs about 34 warrior attacks, so the team must average more than one warrior attack per step.
- Spawning was too slow. The previous version spawned at most one warrior per step, and only when wheat covered every other villager's meal. Spawns are cheap relative to their damage over 30 steps, so the early game should favour them.
- Idle time in the cave was too low. Warriors returned to the village at 3 steps without food, which left some steps with no attacker.

**Changes:**

1. **Multiple spawns per step:** Every available pair of farmers is turned into a warrior spawn while wheat remains above a reserve. The reserve covers next step's meals for all other villagers, so no spawn causes starvation.
2. **Spawn priority over farming:** Farmers are used for spawning first, because a warrior's 3 damage per step outweighs a farmer's 5 wheat per step over the time left. One farmer always stays on the farm to keep wheat income going.
3. **Attack-first warriors:** Any healthy warrior that has eaten recently goes to the cave. Warriors return to eat only when `steps_since_meal` reaches 3, which keeps the starvation margin.
4. **Cave retreat rule:** Warriors with `hp <= 1` retreat, because a 40% Dragon attack would otherwise kill them.
5. **Every villager assigned exactly once** in each call, so the validity checks keep passing.

**Expected effect:** Warrior count should grow faster, and more steps will have attackers present, which should push the win rate up and the win turn down. Starvation is still guarded by the feeding priority and the wheat reserve.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (limited by wheat).
        2. Spawn warriors from farmer pairs as many times as wheat allows,
           keeping a reserve for the next step's meals and one farmer on the farm.
        3. Healthy, recently fed warriors go to the cave to attack.
        4. Everyone else stays on the farm.
      Cave:
        1. Warriors that have not eaten for >= 3 steps, or have hp <= 1, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    EAT_THRESHOLD_VILLAGE = 2
    RETURN_THRESHOLD_CAVE = 3
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    MIN_FARMERS_ON_FARM = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}
        budget = wheat - len(eat)

        others = [c for c in components if id(c) not in eat_ids]

        # 2. Spawn warriors from farmer pairs while wheat covers the reserve.
        spawn_ids = set()
        farmers_free = [c for c in others if c.role == "Farmer"]
        # Keep at least one farmer working on the farm for wheat income.
        max_pairs = max(0, (len(farmers_free) - self.MIN_FARMERS_ON_FARM) // 2)
        pairs = 0
        while pairs < max_pairs:
            reserve = len(others) - 2 * (pairs + 1)  # villagers still needing food later
            if budget - self.WARRIOR_SPAWN_COST < max(0, reserve):
                break
            budget -= self.WARRIOR_SPAWN_COST
            pair = farmers_free[2 * pairs: 2 * pairs + 2]
            for c in pair:
                spawn_ids.add(id(c))
            pairs += 1

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
            if c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```