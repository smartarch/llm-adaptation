from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      Village:
        1. Feed hungry villagers first (limited by wheat).
        2. Spawn warriors from farmer pairs as many times as wheat allows,
           keeping a reserve for the next step's meals and one farmer on the farm.
        3. Healthy, recently fed warriors go to the cave to attack.
        4. Everyone else stays on the farm.
      Cave:
        1. Warriors that have not eaten for >= 3 steps, or have hp <= 1, go home.
        2. Everyone else attacks the Dragon.
    Every component is assigned exactly once per call.
    """

    EAT_THRESHOLD_VILLAGE = 2
    RETURN_THRESHOLD_CAVE = 3
    CAVE_MIN_HP = 2
    WARRIOR_SPAWN_COST = 12
    MIN_FARMERS_ON_FARM = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1. Feed the hungriest villagers first, limited by wheat.
        hungry = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        hungry.sort(key=lambda c: -c.steps_since_meal)
        eat = hungry[:max(0, wheat)]
        eat_ids = {id(c) for c in eat}
        budget = wheat - len(eat)

        others = [c for c in components if id(c) not in eat_ids]

        # 2. Spawn warriors from farmer pairs while wheat covers the reserve.
        spawn_ids = set()
        farmers_free = [c for c in others if c.role == "Farmer"]
        # Keep at least one farmer working on the farm for wheat income.
        max_pairs = max(0, (len(farmers_free) - self.MIN_FARMERS_ON_FARM) // 2)
        pairs = 0
        while pairs < max_pairs:
            reserve = len(others) - 2 * (pairs + 1)  # villagers still needing food later
            if budget - self.WARRIOR_SPAWN_COST < max(0, reserve):
                break
            budget -= self.WARRIOR_SPAWN_COST
            pair = farmers_free[2 * pairs: 2 * pairs + 2]
            for c in pair:
                spawn_ids.add(id(c))
            pairs += 1

        # 3/4. Assign every villager exactly once.
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