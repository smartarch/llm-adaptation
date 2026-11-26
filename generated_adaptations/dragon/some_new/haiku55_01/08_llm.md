## Revised strategy: earlier and more reliable warrior spawning

**What the report shows:**
- All validity checks now pass, so the assignments are legal and every villager is assigned.
- The Dragon is still not killed within 30 steps, so damage output is too low.
- The optional hints show the cause: spawning is too restrictive. Wheat sat unused early (20 to 38), two farmers were not spawned into warriors, and the Warrior count hit zero in several runs. With no warriors, no damage is dealt.

**Diagnosis:**
- The reserve check counted too many villagers. It required wheat for every non-fed villager's future meal, which blocked spawns even when wheat was plentiful.
- Farmers were held back as a fixed "one farmer stays on the farm" rule, so spawns never used the last free pair. Early growth stalled.
- Nothing forced a replacement when no warriors remained.

**Changes:**

1. **Feeding stays first.** Hungry villagers (`steps_since_meal >= 2`) are fed first, most hungry first, limited by available wheat.
2. **Reserve is based on real upcoming need.** The reserve is the number of unfed villagers who will need a meal next step (`steps_since_meal >= 1`), not the whole population. This lets spawns happen whenever the wheat genuinely covers the next meals.
3. **Spawn as many warriors as wheat allows.** Free farmers are paired greedily. One farmer is kept on the farm only when the wheat buffer is thin, so wheat income never fully stops.
4. **Emergency spawn.** If no warriors exist, the spawn check uses a lower reserve, because damage is the only path to victory.
5. **Warrior cycling.** Warriors that were fed recently (`steps_since_meal <= 1`) and are healthy join the attack. Warriors in the cave return when `steps_since_meal >= 3` or `hp <= 1`, which keeps starvation margin.
6. **Every villager is assigned exactly once** in each call.

**Expected effect:** More warriors earlier, with continuous attacks from the cave, should raise total damage enough to kill the Dragon within 30 steps while keeping every villager fed.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed the hungriest villagers first, limited by wheat.
        2. Spawn warriors from free farmer pairs as many times as wheat allows,
           keeping a reserve for the next step's meals. Keep one farmer on the
           farm for wheat income unless the wheat buffer is large.
        3. Recently fed, healthy warriors go to the cave to attack.
        4. Everyone else stays on the farm.
      Cave:
        1. Villagers that have not eaten for >= 3 steps, or have hp <= 1, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    HUNGRY_THRESHOLD = 2        # feed when this many steps have passed without food
    RETURN_THRESHOLD = 3        # leave the cave for food at this many steps
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    SAFETY_BUFFER = 6           # extra wheat needed to spend the last farmer

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

        # Wheat needed next step by villagers who are not fed this step.
        reserve = sum(1 for c in rest if c.steps_since_meal >= 1)

        has_warrior = any(c.role == "Warrior" for c in components)
        free_farmers = [c for c in rest
                        if c.role == "Farmer" and c.steps_since_meal < self.HUNGRY_THRESHOLD]

        # 2. Spawn warriors from farmer pairs while wheat covers the reserve.
        spawn_ids = set()
        idx = 0
        while len(free_farmers) - idx >= 2:
            remaining_after = len(free_farmers) - idx - 2
            # Emergency: no warriors left means damage is the only path to victory.
            needed = reserve if has_warrior else max(0, reserve - 2)
            if remaining_after == 0 and has_warrior:
                needed += self.SAFETY_BUFFER  # spending the last farmer costs wheat income
            if budget - self.WARRIOR_SPAWN_COST < needed:
                break
            budget -= self.WARRIOR_SPAWN_COST
            for c in free_farmers[idx:idx + 2]:
                spawn_ids.add(id(c))
            idx += 2
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
            if c.steps_since_meal >= self.RETURN_THRESHOLD or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```