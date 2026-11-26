## Diagnosis

The only failing tests are `test_no_required_constraints_violated_at_the_end`, which report that the Dragon survived 30 steps. Assignments are valid, every component is assigned, and no one starves, so the problem is still damage throughput.

The last version has two weaknesses:

1. **Too few warriors attack at once.** Spawning uses at most one pair of farmers per step in practice, because the code breaks out of the loop as soon as the reserve check fails once. Early in the game, the 12-wheat cost of a warrior is the real constraint, and the reserve check blocks spawns that would be affordable.
2. **Warriors sit in the Village after eating.** A warrior that has just eaten is sent to the Cave only if its hunger is below 4. Warriors that return from the Cave wait for the next step to be dispatched, and the Cave shift is short, so the Dragon regenerates in the gaps.

I cannot run the simulator here, so I can't confirm the new win rate. The changes below aim at more attacking warriors per step while keeping the starvation and wheat constraints.

## Revised strategy

**Feeding.** Hungry villagers (`steps_since_meal >= 2`) eat in the Village, most hungry first, limited by the wheat stock. Anyone who cannot eat stays on the farm.

**Spawning.** Up to three spawn pairs per step, taken from idle farmers only. A spawn is accepted when the wheat left afterwards covers the meals due next step, counting villagers in the Village and warriors returning from the Cave. Keeping at least one farmer on the farm preserves wheat income.

**Attacking.** Every fed, healthy warrior in the Village goes to the Cave. Warriors stay until they reach 4 steps without food or 2 HP or less, so the 6-step starvation limit still holds.

**Assignments.** Each component is assigned exactly once per step, with a fallback to "farm".

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: maximize warriors attacking each step while keeping
    every villager fed inside the 6-step starvation window.

    - Hungry villagers eat in the Village, most hungry first, within wheat stock.
    - Idle farmers form up to MAX_SPAWNS_PER_STEP spawn pairs (12 wheat each),
      keeping at least one farmer on the farm and enough wheat for next step's meals.
    - Fed, healthy warriors go to the Cave and attack; they leave when hungry or hurt.
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
                assignment[id(c)] = "farm"

        # Meals expected next step: villagers nearly hungry, plus warriors
        # currently in the Cave that will come back to eat.
        village_due = sum(
            1 for c in components
            if id(c) not in assignment and c.steps_since_meal + 1 >= self.EAT_IN_VILLAGE
        )
        cave_returning = sum(1 for w in environment.warriors if w.location == "Cave")
        cave_returning += sum(1 for f in environment.farmers if f.location == "Cave")
        reserve_next = village_due + cave_returning

        # 2) Spawn from idle farmers, keeping at least one farmer farming.
        free_farmers = [
            c for c in components
            if id(c) not in assignment and c.role == "Farmer"
        ]
        spawns = 0
        used = 0
        while (
            spawns < self.MAX_SPAWNS_PER_STEP
            and len(free_farmers) - used - 2 >= 1
        ):
            if budget - self.WARRIOR_COST < reserve_next:
                break
            for c in free_farmers[used:used + 2]:
                assignment[id(c)] = "spawn warrior"
            used += 2
            budget -= self.WARRIOR_COST
            spawns += 1

        # 3) Remaining villagers: healthy warriors attack, everyone else farms.
        for c in components:
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