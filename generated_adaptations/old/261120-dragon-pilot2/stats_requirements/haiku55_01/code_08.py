import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2 (1 wheat each).
      - Spawn warriors in parallel: every disjoint pair of idle villagers (farmers
        preferred) goes to "spawn warrior" while wheat covers cost + meals.
        Farmers are spawned only after the warrior target is reached.
      - Fed warriors (steps_since_meal < 2) go to the Cave to maximize attackers.
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # Count warriors that exist (in village; cave ones are not visible here,
        # so we use the spawn counter plus visible warriors as an estimate).
        visible_warriors = sum(1 for c in components if c.role == "Warrior")
        total_warriors = visible_warriors + self.warriors_spawned * 0  # visible is authoritative
        total_warriors = max(total_warriors, getattr(self, "_known_warriors", 0))

        # 2) Spawning in parallel: pair up idle villagers.
        idle = [c for c in components if c not in assigned]
        farmers_idle = [c for c in idle if c.role == "Farmer"]
        warriors_idle = [c for c in idle if c.role == "Warrior"]

        if total_warriors < self.WARRIOR_TARGET:
            pool = farmers_idle + warriors_idle
            i = 0
            while (i + 1 < len(pool) and total_warriors < self.WARRIOR_TARGET
                   and budget >= self.WARRIOR_COST):
                a, b = pool[i], pool[i + 1]
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                assigned.add(a)
                assigned.add(b)
                budget -= self.WARRIOR_COST
                total_warriors += 1
                self.warriors_spawned += 1
                i += 2
        elif self.farmers_spawned < self.FARMER_TARGET and budget >= self.FARMER_COST:
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

        self._known_warriors = total_warriors

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")