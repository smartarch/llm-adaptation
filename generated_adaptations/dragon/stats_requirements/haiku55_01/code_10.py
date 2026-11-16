import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2 (1 wheat each, budgeted first).
      - Spawn warriors up to WARRIOR_TARGET using idle villagers in pairs
        (farmers preferred), only when wheat covers cost + reserved meals.
        Total warriors = warriors in Village + warriors that stayed in Cave.
      - Fed warriors (steps_since_meal < 2) go to the Cave while it has room.
      - Everyone else farms.
    Cave:
      - Warriors with steps_since_meal <= 3 attack.
      - Warriors at 4+ steps since meal return to the Village to eat.
      - Farmers never fight; any farmer in the Cave returns to the Village.
    """

    EAT_THRESHOLD = 2
    CAVE_RETURN_HUNGER = 4      # attack while steps_since_meal < 4
    WARRIOR_TARGET = 8
    FARMER_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10
    MIN_ATTACKERS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self._cave_attackers = 0   # warriors that stayed in the Cave last cave phase

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # Reserve wheat for meals that will be needed next step by warriors/farmers
        # that are not eating now (conservative: 1 each).
        reserve = 0

        # 2) Warrior count: village warriors + warriors that remained in the Cave.
        village_warriors = sum(1 for c in components if c.role == "Warrior")
        total_warriors = village_warriors + self._cave_attackers

        idle = [c for c in components if c not in assigned]
        farmers_idle = [c for c in idle if c.role == "Farmer"]
        warriors_idle = [c for c in idle if c.role == "Warrior"]

        # Spawn warriors in pairs while below target and affordable.
        if total_warriors < self.WARRIOR_TARGET:
            pool = farmers_idle + warriors_idle
            i = 0
            while (i + 1 < len(pool)
                   and total_warriors < self.WARRIOR_TARGET
                   and budget - reserve >= self.WARRIOR_COST):
                a, b = pool[i], pool[i + 1]
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                assigned.add(a)
                assigned.add(b)
                budget -= self.WARRIOR_COST
                total_warriors += 1
                i += 2

        # Spawn farmers only after the warrior target is reached.
        elif (self.farmers_spawned < self.FARMER_TARGET
              and budget - reserve >= self.FARMER_COST):
            farmers_idle = [c for c in components if c not in assigned and c.role == "Farmer"]
            if len(farmers_idle) >= 2:
                environment.assign_group(farmers_idle[0], "spawn farmer")
                environment.assign_group(farmers_idle[1], "spawn farmer")
                assigned.add(farmers_idle[0])
                assigned.add(farmers_idle[1])
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Remaining villagers: fed warriors to the Cave, everyone else farms.
        for c in components:
            if c in assigned:
                continue
            if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
                attackers += 1
            else:
                environment.assign_group(c, "village")
        self._cave_attackers = attackers