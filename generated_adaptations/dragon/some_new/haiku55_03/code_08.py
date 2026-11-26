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