from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: maximize warrior output and keep the Dragon under
    continuous attack, while keeping every villager fed.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Spare farmers spawn warriors (2 farmers per warrior, 12 wheat each),
      limited by the wheat left after meals and by a per-step spawn cap.
    - Fed, healthy warriors go to the Cave to attack.
    - Warriors leave the Cave when hungry or badly hurt; farmers never fight.
    """

    FEED_THRESHOLD = 3        # eat when steps_since_meal reaches this
    LOW_HP = 2                # warriors at or below this HP stop fighting
    WARRIOR_SPAWN_COST = 12
    MAX_SPAWNS_PER_STEP = 2   # warriors spawned per step at most
    MIN_FARMERS_FARMING = 1   # keep at least this many farmers producing wheat

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        # Wheat left after paying for this step's meals.
        budget = wheat - len(eat)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        # Decide how many warriors to spawn this step.
        # Each spawn needs 2 farmers in the spawn group; keep some farmers farming.
        max_by_wheat = max(0, budget // self.WARRIOR_SPAWN_COST)
        max_by_farmers = max(0, (len(farmers) - self.MIN_FARMERS_FARMING) // 2)
        num_spawns = min(self.MAX_SPAWNS_PER_STEP, max_by_wheat, max_by_farmers)

        spawn_group = farmers[: 2 * num_spawns]
        spawn_ids = {id(c) for c in spawn_group}

        # Warriors that are fed and healthy go to the Cave; the rest farm.
        cave_group, farm_group = [], []
        for c in warriors:
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