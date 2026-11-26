## Diagnosis

The required failures are all `test_no_required_constraints_violated_at_the_end` with "the Dragon must be killed". The game is ending without a kill, so the problem is damage output and timing, not starvation or invalid assignments. The system and starvation tests pass in every run, so the feeding logic can stay as it is.

The last version has three weaknesses:

1. **Spawn reserve is too strict.** It requires `budget - cost >= population + spawns + 1`. With 16 wheat and 4 villagers, a warrior is never spawned, so the attacker count stays low. This is also why the optional spawn hints fail.
2. **Spawning is rate-limited by the reserve rule, not by real need.** Meals cost about one wheat per villager every three steps, so keeping half the population's worth of wheat in reserve is enough. Requiring a full meal per villager is too conservative.
3. **Spawns take warriors out of the attack.** With fewer than two idle farmers, the pool falls back to warriors, which is correct, but the code does not account for this when deciding how many attackers are left.

## Revised strategy

**Feeding.** Villagers with `steps_since_meal >= 3` eat in the Village. Meal wheat is subtracted from the budget before any spawn decision, so feeding always has priority.

**Spawning.** Spawn pairs come from idle farmers first, with warriors only as a fallback. Up to 2 warriors are spawned per step. A spawn is allowed when the wheat left after the spawn is at least half the population, which keeps enough reserve for meals without blocking early growth.

**Attack.** Every fed, healthy warrior in the Village goes to the Cave, which maximises damage per step. Warriors that are hungry or at 2 HP or less retreat to the Village. Farmers never attack.

**Regeneration.** Keeping as many warriors attacking as possible each step minimises the steps in which nobody attacks, so the Dragon regenerates less.

**Constraints.** A villager spends at most 3 steps in the Cave before it is sent to eat, so every villager eats within the 6-step starvation window.

I can't run the simulator, so the win rate is not verified. The changes target the required failures: faster warrior growth, more attackers on the Dragon each step, and a more permissive spawn reserve.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: grow the warrior force quickly, keep as many warriors
    as possible attacking every step, and keep everyone fed.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Idle farmers form spawn pairs (2 per warrior, 12 wheat each), with
      warriors as a fallback. Up to MAX_SPAWNS_PER_STEP warriors per step.
    - Fed, healthy warriors go to the Cave and attack.
    - Hungry or badly hurt warriors return to the Village. Farmers never fight.
    """

    FEED_THRESHOLD = 3        # eat when steps_since_meal reaches this
    LOW_HP = 2                # warriors at or below this HP stop fighting
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        population = len(environment.farmers) + len(environment.warriors)

        # 1) Feed anyone who is due a meal. Meals are paid first.
        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        budget = wheat - len(eat)

        # 2) Spawn pool: idle farmers first, warriors as a fallback.
        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]
        pool = farmers + warriors

        spawn_group = []
        spawns = 0
        reserve = population // 2
        while spawns < self.MAX_SPAWNS_PER_STEP and len(pool) - len(spawn_group) >= 2:
            cost = self.WARRIOR_COST * (spawns + 1)
            # Keep a reserve of wheat so meals stay affordable after spawning.
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