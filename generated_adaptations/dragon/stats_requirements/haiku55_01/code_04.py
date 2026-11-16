import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2.
      - Spawn warriors early (farmers used as spawners, they are not consumed),
        keeping enough wheat to feed everyone. Spawn farmers only after the
        warrior target is reached.
      - Fed warriors go to the Cave until enough attackers are there;
        the rest wait in the Village (rotation keeps attacks almost every step).
      - Farmers keep farming.
    Cave:
      - Warriors with steps_since_meal < 3 attack (staggered by count target).
      - Hungrier warriors and all farmers return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 2
    CAVE_RETURN_HUNGER = 3
    WARRIOR_TARGET = 5
    FARMER_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10
    MIN_CAVE_ATTACKERS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def _count(self, components, role):
        return sum(1 for c in components if c.role == role)

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # 2) Spawning (one spawn group per step, leaving wheat for feeding).
        total_warriors = self.warriors_spawned + self._count(components, "Warrior")
        free = [c for c in components if c not in assigned]
        farmers_free = [c for c in free if c.role == "Farmer"]
        others_free = [c for c in free if c.role != "Farmer"]
        reserve = len(components)  # keep wheat for next step's meals

        if total_warriors < self.WARRIOR_TARGET and budget - reserve >= self.WARRIOR_COST:
            spawners = (farmers_free + others_free)[:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn warrior")
                    assigned.add(c)
                budget -= self.WARRIOR_COST
                self.warriors_spawned += 1
        elif (self.farmers_spawned < self.FARMER_TARGET
              and total_warriors >= self.WARRIOR_TARGET
              and budget - reserve >= self.FARMER_COST):
            spawners = [c for c in farmers_free if c not in assigned][:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn farmer")
                    assigned.add(c)
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Everyone else.
        remaining = [c for c in components if c not in assigned]
        fed_warriors = [c for c in remaining
                        if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE]
        cave_now = getattr(self, "_cave_count", 0)
        want_in_cave = max(self.MIN_CAVE_ATTACKERS, (len(fed_warriors) + cave_now + 1) // 2)
        slots = max(0, want_in_cave - cave_now)

        for c in remaining:
            if c in fed_warriors and slots > 0:
                environment.assign_group(c, "cave")
                slots -= 1
            else:
                environment.assign_group(c, "farm")

        self._cave_count = 0  # recomputed in the cave phase

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
                attackers += 1
            elif c.role == "Warrior":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "village")
        self._cave_count = attackers