from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Sustained warrior pressure:
      - Villagers that have not eaten for >= 3 steps eat in the Village.
      - One farmer is spawned early (requirement), then warriors are spawned
        whenever wheat allows (up to MAX_WARRIOR_SPAWNS), using two farmers as spawners.
      - Fed warriors go to the Cave; warriors in the Cave attack every step
        unless they have gone 4+ steps without eating, in which case they return to eat.
      - Farmers in the Cave are sent back to the Village.
    """

    MAX_WARRIOR_SPAWNS = 10
    MAX_FARMER_SPAWNS = 1
    EAT_THRESHOLD = 3          # Village: eat when steps_since_meal >= this
    CAVE_SAFE_THRESHOLD = 2    # Village: only send warriors to the Cave if steps_since_meal <= this
    CAVE_RETURN_THRESHOLD = 4  # Cave: go eat when steps_since_meal >= this

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        n = len(components)
        plan = [None] * n
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1) Eat first: villagers who are getting hungry.
        for i, c in enumerate(components):
            if c.steps_since_meal >= self.EAT_THRESHOLD and wheat >= 1:
                plan[i] = "eat"
                wheat -= 1

        def free(role=None):
            return [i for i, c in enumerate(components)
                    if plan[i] is None and (role is None or c.role == role)]

        # 2) One early farmer spawn (requirement, and adds wheat income).
        if self.farmers_spawned < self.MAX_FARMER_SPAWNS and wheat >= 10:
            spawners = free("Farmer")[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn farmer"
                wheat -= 10
                self.farmers_spawned += 1

        # 3) Warrior spawns whenever wheat allows (damage dealers).
        if self.warriors_spawned < self.MAX_WARRIOR_SPAWNS and wheat >= 12:
            spawners = free("Farmer")[:2]
            if len(spawners) < 2:
                spawners = free()[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn warrior"
                wheat -= 12
                self.warriors_spawned += 1

        # 4) Fed, unassigned warriors go to the Cave while the Dragon lives.
        for i, c in enumerate(components):
            if plan[i] is None and c.role == "Warrior":
                if dragon_alive and c.steps_since_meal <= self.CAVE_SAFE_THRESHOLD:
                    plan[i] = "cave"

        # 5) Everyone else farms.
        for i in range(n):
            if plan[i] is None:
                plan[i] = "farm"

        for c, g in zip(components, plan):
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                group = "village"
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(c, group)