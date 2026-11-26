from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy with aggressive warrior spawning.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Idle farmers form spawn pairs (2 per warrior, 12 wheat each). Spawns
      happen whenever wheat still covers one meal per villager afterwards.
    - Fed, healthy warriors attack in the Cave; hungry or hurt warriors
      return to the Village. Farmers never fight.
    """

    FEED_THRESHOLD = 3       # eat when steps_since_meal reaches this
    LOW_HP = 2               # warriors at or below this HP stop fighting
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        population = len(environment.farmers) + len(environment.warriors)

        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        # Wheat available after paying for this step's meals.
        budget = wheat - len(eat)

        # Spawn pool: idle farmers first, then idle warriors if needed.
        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]
        pool = farmers + warriors

        spawn_group = []
        spawns = 0
        while (
            spawns < self.MAX_SPAWNS_PER_STEP
            and len(pool) - len(spawn_group) >= 2
        ):
            new_cost = self.WARRIOR_COST * (spawns + 1)
            # Keep one meal of wheat for every villager after the spawn.
            if budget - new_cost < population + spawns + 1:
                break
            # Take two villagers for this spawn.
            spawn_group.extend(pool[len(spawn_group): len(spawn_group) + 2])
            spawns += 1

        spawn_ids = {id(c) for c in spawn_group}

        # Fed, healthy warriors go to the Cave; everyone else farms.
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