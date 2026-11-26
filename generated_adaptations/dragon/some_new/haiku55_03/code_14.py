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