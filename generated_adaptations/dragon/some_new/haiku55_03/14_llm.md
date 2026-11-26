## Diagnosis

The failures have two causes.

1. **Invalid meal assignments.** The feeding list ignored the wheat stock. When wheat ran out, the code still assigned villagers to "eat", which the environment rejects.
2. **Unassigned components.** The spawn and dispatch logic built several overlapping lists and only assigned villagers that landed in one of them. Any villager that slipped through was never assigned, which broke `test_all_assigned`.

The required-constraint failures are also tied to wheat. In one run, wheat hit 0 while a villager still needed a meal the next step. Spawning must leave enough wheat for the meals that come due.

The "Dragon must be killed" failures remain the main issue for the win rate. The changes below make the assignments valid and complete, and they keep the attack logic close to the version that had the highest win rate, so I have not claimed a higher win rate.

## Revised strategy

**Single assignment table.** Each step, every villager is first recorded in one dictionary keyed by identity. Each one gets exactly one group, and a final fallback sends any leftover villager to "farm". This removes the unassigned-component failures.

**Meals limited by wheat.** Hungry villagers are sorted by `steps_since_meal` (most hungry first). Each one is assigned to "eat" only while wheat remains. Anyone who cannot be fed stays on the farm and keeps producing wheat.

**Spawning with a reserve.** A spawn pair is formed from idle farmers, with warriors used only if farmers are short. A spawn is allowed only if the wheat left afterwards covers the meals due next step, so the starvation constraint holds.

**Cave.** Healthy warriors attack. A warrior returns to the Village when it reaches 4 steps without a meal or drops to 2 HP or less. Farmers never enter the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy with valid, complete assignments.

    - Hungry villagers eat in the Village, most hungry first, but only as
      many as the wheat stock can pay for.
    - Idle farmers form spawn pairs for warriors (12 wheat each), with a
      wheat reserve for the meals that come due next step.
    - Healthy warriors attack from the Cave and return when hungry or hurt.
    - Every component is assigned exactly once per step.
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

        # 1) Meals, most hungry first, limited by available wheat.
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
                assignment[id(c)] = "farm"  # cannot be fed; keep farming

        # Villagers who will be due for food next step must be covered.
        due_next = sum(
            1 for c in components
            if c.steps_since_meal + 1 >= self.EAT_IN_VILLAGE
        )

        # 2) Spawning from idle farmers, warriors only as fallback.
        free = [c for c in components if id(c) not in assignment]
        farmers = [c for c in free if c.role == "Farmer"]
        warriors = [c for c in free if c.role == "Warrior"]
        pool = farmers if len(farmers) >= 2 else farmers + warriors

        spawns = 0
        used = 0
        while spawns < self.MAX_SPAWNS_PER_STEP and len(pool) - used >= 2:
            if budget - self.WARRIOR_COST < due_next:
                break
            for c in pool[used:used + 2]:
                assignment[id(c)] = "spawn warrior"
            used += 2
            budget -= self.WARRIOR_COST
            spawns += 1

        # 3) Remaining warriors: healthy ones attack, others farm.
        for c in components:
            if id(c) in assignment:
                continue
            if c.role == "Warrior" and c.hp > self.LOW_HP \
                    and c.steps_since_meal < self.CAVE_MAX_HUNGER:
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