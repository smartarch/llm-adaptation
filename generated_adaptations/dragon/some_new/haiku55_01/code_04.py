from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed the hungriest villagers first, but never more meals than wheat allows.
        2. Spawn a warrior (pair of farmers in 'spawn warrior') only if the wheat
           left after the spawn still covers every other villager's next meal.
        3. Fed, healthy warriors go to the 'cave' to attack.
        4. Everyone else (including unfed villagers) stays on the 'farm'.
      Cave:
        1. Villagers without a meal for >= 3 steps, or with hp <= 1, return to 'village'.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    EAT_THRESHOLD_VILLAGE = 2     # feed when this many steps have passed without food
    RETURN_THRESHOLD_CAVE = 3     # leave the cave for food at this many steps
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by available wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}

        budget = wheat - len(eat)
        others = [c for c in components if id(c) not in eat_ids]

        # 2. Spawn a warrior only if enough wheat remains to feed the others next step.
        spawn_ids = set()
        reserve = len(others)
        candidates = [c for c in others if c.role == "Farmer" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE]
        if len(candidates) >= 2 and budget - self.WARRIOR_SPAWN_COST >= reserve:
            for c in candidates[:2]:
                spawn_ids.add(id(c))

        # 3/4. Assign every remaining villager exactly once.
        for c in components:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif (c.role == "Warrior"
                  and c.hp >= self.CAVE_MIN_HP
                  and c.steps_since_meal <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")