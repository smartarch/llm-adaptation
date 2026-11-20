from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors attack in the Cave while steps_since_meal < 4, then walk back to the Village
      (arriving at count 5) and eat before the 6-step starvation limit.
    - Meals are assigned first, most urgent (highest steps_since_meal) first, so no one starves.
    - Every step, idle farmers are paired into "spawn warrior" groups while wheat above
      a meal reserve covers 12 wheat per pair.
    - Farmers never enter the Cave; they farm wheat when not eating or spawning.
    """

    WARRIOR_LEAVE_CAVE_AT = 4
    FARMER_EAT_AT = 3
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals: warriors that are not freshly fed, farmers at the threshold.
        #    Most urgent first, so that starving risk is handled before anything else.
        candidates = [c for c in warriors if c.steps_since_meal >= 1]
        candidates += [c for c in farmers if c.steps_since_meal >= self.FARMER_EAT_AT]
        candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        eaters = candidates[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Small wheat reserve for the next step's meals.
        reserve = len(warriors) // 2 + 1

        # 3) Greedy warrior spawning from pairs of idle farmers.
        spawn_ids = set()
        pool = list(idle_farmers)
        while len(pool) >= 2 and wheat - reserve >= self.WARRIOR_COST:
            pair = pool[:2]
            pool = pool[2:]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 4) Fresh warriors go to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 5) Remaining farmers farm.
        for c in idle_farmers:
            if id(c) not in spawn_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")