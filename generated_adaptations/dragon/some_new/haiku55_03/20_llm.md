## Diagnosis

The last version fell to a 0% win rate. The cause is in the spawn logic. Its condition `len(free_farmers) - used - 2 >= 1` always keeps one farmer farming, so with only two idle farmers it never spawns. The game then has no warriors, nothing attacks the Dragon, and the warrior-replacement tests fail.

The spawn rule also makes the strategy more fragile than it needs to be. Spawning does not consume the two villagers in the spawn group. Those two farmers can spawn a warrior every step as long as wheat allows. Wheat is the real limit, so the strategy should spend wheat on warriors whenever it can, while keeping enough for the meals that come due.

## Revised strategy

**Feeding.** Villagers with `steps_since_meal >= 2` eat in the Village, most hungry first, limited by the wheat stock. Anyone who cannot eat farms.

**Spawn pool.**
- With three or more idle farmers, one farmer stays on the farm for wheat income and the rest form the spawn pool.
- With exactly two idle farmers and no warriors alive, both form the pool, so the game can always replace a lost warrior.
- Otherwise, idle warriors in the Village serve as the pool.

**Spawn budget.** Each spawn costs 12 wheat. The number of spawns is limited to `(wheat after meals - reserve) // 12`, where the reserve is the number of villagers due for a meal next step. This keeps the starvation constraint satisfied. Spawns are capped at three per step.

**Attacking.** Fed, healthy warriors not used for spawning go to the Cave. They leave when they reach 4 steps without food or drop to 2 HP or less. Farmers never enter the Cave.

**Assignments.** Every component receives exactly one group per step.

I cannot run the simulator or the unit tests here, so the win rate and test results are not verified. This version restores spawning whenever two spawn candidates and enough wheat are available, which was the failure mode of the last two versions.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: spawn warriors whenever wheat and spawn candidates
    allow it, attack with healthy warriors, and keep everyone fed.

    - Hungry villagers eat in the Village, most hungry first, within wheat stock.
    - One farmer stays on the farm when possible; the other idle farmers form
      spawn pairs (12 wheat per warrior). Warriors are used as spawn material
      only when no farmer pool is available.
    - A spawn is only made if the wheat left afterwards covers the meals due
      next step.
    - Healthy, fed warriors attack from the Cave; they leave when hungry or hurt.
    - Farmers never enter the Cave.
    """

    EAT_IN_VILLAGE = 2        # eat in the Village once this hungry
    CAVE_MAX_HUNGER = 4       # warriors leave the Cave at this hunger level
    LOW_HP = 2                # warriors at or below this HP retreat
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignment = {}

        # 1) Meals first, most hungry first, limited by available wheat.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_IN_VILLAGE],
            key=lambda c: -c.steps_since_meal,
        )
        budget = wheat
        for c in hungry:
            if budget >= 1:
                assignment[id(c)] = "eat"
                budget -= 1
            else:
                assignment[id(c)] = "farm"

        free = [c for c in components if id(c) not in assignment]

        # Reserve: meals due next step among villagers in the Village,
        # plus everyone currently in the Cave who will return to eat.
        reserve = sum(
            1 for c in free if c.steps_since_meal + 1 >= self.EAT_IN_VILLAGE
        )
        reserve += sum(1 for v in environment.warriors if v.location == "Cave")
        reserve += sum(1 for v in environment.farmers if v.location == "Cave")

        # 2) Build the spawn pool.
        farmers_free = [c for c in free if c.role == "Farmer"]
        warriors_free = [c for c in free if c.role == "Warrior"]
        warriors_alive = len(environment.warriors)

        if len(farmers_free) >= 3:
            pool = farmers_free[1:]          # keep one farmer producing wheat
        elif len(farmers_free) == 2 and warriors_alive == 0:
            pool = farmers_free              # rebuild the army
        else:
            pool = []
        if len(pool) < 2:
            pool = warriors_free             # fall back to warriors

        # 3) Spawn as many warriors as wheat and the reserve allow.
        affordable = max(0, (budget - reserve) // self.WARRIOR_COST)
        n_spawn = min(len(pool) // 2, self.MAX_SPAWNS_PER_STEP, affordable)
        for i in range(n_spawn):
            for c in pool[2 * i: 2 * i + 2]:
                assignment[id(c)] = "spawn warrior"

        # 4) Remaining villagers: healthy warriors attack, everyone else farms.
        for c in free:
            if id(c) in assignment:
                continue
            if (
                c.role == "Warrior"
                and c.hp > self.LOW_HP
                and c.steps_since_meal < self.CAVE_MAX_HUNGER
            ):
                assignment[id(c)] = "cave"
            else:
                assignment[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignment.get(id(c), "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_MAX_HUNGER or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```