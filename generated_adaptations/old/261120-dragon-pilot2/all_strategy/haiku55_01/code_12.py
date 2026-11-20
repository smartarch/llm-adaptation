import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Meals first: warriors eat at >= 2 steps since last meal, farmers at >= 3,
        and anyone at >= 4 is fed first.
      - Fed warriors that are not eating go to the Cave to attack. Hungry warriors
        that could not eat (no wheat) stay in the Village.
      - Spawning uses wheat left after meals, with a small reserve (about a third
        of the villagers, at least 2). Spawn pairs are tracked so that:
          * the first two Warriors are spawned as early as possible (early attacks),
          * at least one Farmer is spawned (wheat income),
          * then more Farmers while there are few, and Warriors with leftover wheat.
      - In the Cave, a warrior starts heading back at >= 2 steps since its last
        meal (at 2 only if another warrior stays to attack). At >= 3 it always returns.
      - Remaining farmers farm in the Village.
    """

    WARRIOR_EAT_THRESHOLD = 2
    FARMER_EAT_THRESHOLD = 3
    CRITICAL_HUNGER = 4
    CAVE_SOFT_RETURN = 2
    CAVE_FORCED_RETURN = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    TARGET_FARMERS = 4
    MIN_WARRIOR_SPAWNS = 2
    MIN_FARMER_SPAWNS = 1
    KEEP_FARMING = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        if step <= 1:
            self.warriors_spawned = 0
            self.farmers_spawned = 0

        wheat = environment.farm.wheat
        assigned = set()

        # 1) Meals first, most-starved first.
        def needs_meal(c):
            if c.steps_since_meal >= self.CRITICAL_HUNGER:
                return True
            if c.role == "Warrior":
                return c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            return c.steps_since_meal >= self.FARMER_EAT_THRESHOLD

        hungry = sorted(
            [c for c in components if needs_meal(c)],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat >= 1:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat -= 1

        remaining = [c for c in components if id(c) not in assigned]

        # 2) Fed warriors (not hungry, not eating) go to the Cave to attack.
        #    Hungry warriors that could not eat stay in the Village.
        for c in remaining:
            if c.role == "Warrior" and not needs_meal(c):
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        remaining = [c for c in components if id(c) not in assigned]

        # 3) Spawning, funded by wheat left after meals.
        reserve = max(2, math.ceil(len(components) / 3))
        spare = wheat - reserve
        farmers_total = sum(1 for c in components if c.role == "Farmer")

        candidates = [
            c for c in remaining
            if c.role == "Farmer" and c.steps_since_meal < self.FARMER_EAT_THRESHOLD
        ]
        # Keep some farmers on the farm to keep wheat income flowing.
        pool = candidates[self.KEEP_FARMING:]
        idx = 0

        def spawn_pair(group):
            nonlocal idx
            for c in pool[idx:idx + 2]:
                environment.assign_group(c, group)
                assigned.add(id(c))
            idx += 2

        # a) Early Warriors until the minimum is reached.
        while (self.warriors_spawned < self.MIN_WARRIOR_SPAWNS
               and len(pool) - idx >= 2 and spare >= self.WARRIOR_COST):
            spawn_pair("spawn warrior")
            self.warriors_spawned += 1
            spare -= self.WARRIOR_COST

        # b) At least one Farmer for wheat income.
        while (self.farmers_spawned < self.MIN_FARMER_SPAWNS
               and len(pool) - idx >= 2 and spare >= self.FARMER_COST):
            spawn_pair("spawn farmer")
            self.farmers_spawned += 1
            farmers_total += 1
            spare -= self.FARMER_COST

        # c) More Farmers while the farmer count is low.
        while (farmers_total < self.TARGET_FARMERS
               and len(pool) - idx >= 2 and spare >= self.FARMER_COST):
            spawn_pair("spawn farmer")
            self.farmers_spawned += 1
            farmers_total += 1
            spare -= self.FARMER_COST

        # d) Warriors with any leftover wheat.
        while len(pool) - idx >= 2 and spare >= self.WARRIOR_COST:
            spawn_pair("spawn warrior")
            self.warriors_spawned += 1
            spare -= self.WARRIOR_COST

        # 4) Everyone else farms in the Village (including hungry warriors
        #    that could not eat, which stay home).
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        for c in farmers:
            environment.assign_group(c, "village")

        returning = set()
        # Most hungry first.
        for c in sorted(warriors, key=lambda w: w.steps_since_meal, reverse=True):
            if c.steps_since_meal >= self.CAVE_FORCED_RETURN:
                returning.add(id(c))
            elif c.steps_since_meal >= self.CAVE_SOFT_RETURN:
                attackers_left = len(warriors) - len(returning) - 1
                if attackers_left >= 1:
                    returning.add(id(c))

        for c in warriors:
            if id(c) in returning:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")