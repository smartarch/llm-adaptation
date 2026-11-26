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