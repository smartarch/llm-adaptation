## Diagnosis

The four required failures are all `test_no_required_constraints_violated_at_the_end` with "the Dragon must be killed". The game reaches step 30 with the Dragon still alive. The starvation and assignment tests pass, so feeding is correct and the problem is damage throughput.

The main causes are:

1. **Spawn rate is capped too low.** At most 2 warriors are spawned per step, and the reserve rule holds back spawns in the early game when wheat is most useful.
2. **Warriors are taken from the attack force.** When the spawn pool falls back to warriors, those attackers stop hitting the Dragon for that step.
3. **Attack time per warrior is short.** A warrior attacks only while `steps_since_meal < 3`, so each warrior attacks about 2 of every 4 steps.

## Revised strategy

**Feeding (unchanged).** Villagers with `steps_since_meal >= 3` eat in the Village. Meal wheat is paid first, so feeding always takes priority over spawning.

**Spawning (more aggressive).**
- Up to 3 warriors per step, up from 2.
- Spawn pairs come from idle farmers only. Warriors are used as a spawn pool only when fewer than two farmers are available, which keeps the attack force intact.
- The wheat reserve is `population // 2` after the spawn, which keeps meals affordable but allows earlier growth.

**Attacking (unchanged).** Fed, healthy warriors in the Village go to the Cave. Warriors that are hungry or at 2 HP or less return to the Village. Farmers never fight.

**Constraints.** A villager spends at most 3 steps in the Cave before it returns and eats, so every villager eats within the 6-step starvation limit.

I can't run the simulator here, so the win rate is not verified. The changes aim at the failing requirement by building a larger attack force faster and keeping warriors out of the spawn pool when farmers are available.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: grow the warrior force quickly and keep as many
    warriors attacking as possible, while keeping everyone fed.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Idle farmers form spawn pairs (2 per warrior, 12 wheat each). Warriors
      are only used as spawn material when too few farmers are available.
    - Fed, healthy warriors go to the Cave and attack.
    - Hungry or badly hurt warriors return to the Village. Farmers never fight.
    """

    FEED_THRESHOLD = 3        # eat when steps_since_meal reaches this
    LOW_HP = 2                # warriors at or below this HP stop fighting
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        population = len(environment.farmers) + len(environment.warriors)

        # 1) Feed anyone due a meal. Meals are paid first.
        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        budget = wheat - len(eat)

        # 2) Spawn pool: idle farmers first; warriors only as a fallback.
        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]
        pool = farmers if len(farmers) >= 2 else farmers + warriors

        spawn_group = []
        spawns = 0
        reserve = population // 2
        while spawns < self.MAX_SPAWNS_PER_STEP and len(pool) - len(spawn_group) >= 2:
            cost = self.WARRIOR_COST * (spawns + 1)
            # Keep a wheat reserve so meals stay affordable after spawning.
            if budget - cost < reserve:
                break
            spawn_group.extend(pool[len(spawn_group): len(spawn_group) + 2])
            spawns += 1

        spawn_ids = {id(c) for c in spawn_group}

        # 3) Fed, healthy warriors attack from the Cave; everyone else farms.
        cave_group, farm_group = [], []
        for c in warriors:
            if id(c) in spawn_ids:
                continue
            if c.hp > self.LOW_HP and c.steps_since_meal < self.FEED_THRESHOLD:
                cave_group.append(c)
            else:
                farm_group.append(c)
        for c in farmers:
            if id(c) not in spawn_ids:
                farm_group.append(c)

        for c in eat:
            environment.assign_group(c, "eat")
        for c in spawn_group:
            environment.assign_group(c, "spawn warrior")
        for c in cave_group:
            environment.assign_group(c, "cave")
        for c in farm_group:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.FEED_THRESHOLD or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```