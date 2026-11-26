from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: maximize attack uptime in the Cave, grow the warrior
    force quickly, and keep every villager fed within the starvation window.

    - Villagers with steps_since_meal >= EAT_IN_VILLAGE eat when in the Village.
    - Warriors stay in the Cave until steps_since_meal >= CAVE_MAX_HUNGER
      or hp <= LOW_HP, which gives longer attack shifts than a shorter cycle.
    - Idle farmers form spawn pairs (2 per warrior, 12 wheat each); warriors
      are used as spawn material only when farmers are short.
    - Farmers never fight.
    """

    EAT_IN_VILLAGE = 2        # eat in the Village once this hungry
    CAVE_MAX_HUNGER = 4       # leave the Cave at this hunger level
    LOW_HP = 2                # warriors at or below this HP retreat
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Feed everyone who is due. Meals are paid first.
        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.EAT_IN_VILLAGE:
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
        while spawns < self.MAX_SPAWNS_PER_STEP and len(pool) - len(spawn_group) >= 2:
            cost = self.WARRIOR_COST * (spawns + 1)
            # Only keep enough wheat for the meals of the villagers in the Village.
            if budget - cost < 0:
                break
            spawn_group.extend(pool[len(spawn_group): len(spawn_group) + 2])
            spawns += 1

        spawn_ids = {id(c) for c in spawn_group}

        # 3) Fed, healthy warriors go to the Cave; everyone else farms.
        cave_group, farm_group = [], []
        for c in warriors:
            if id(c) in spawn_ids:
                continue
            if c.hp > self.LOW_HP and c.steps_since_meal < self.CAVE_MAX_HUNGER:
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
            elif c.steps_since_meal >= self.CAVE_MAX_HUNGER or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")