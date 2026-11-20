from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Eat-first, warrior-focused strategy:
      - Villagers who have not eaten for >= 2 steps eat first (keeps them far from starvation).
      - Warriors are spawned early (up to 4 spawned), farmers spawned once for wheat income.
      - Warriors that are fed (steps_since_meal <= 2) go to the Cave to attack.
      - In the Cave, warriors that have not eaten for >= 4 steps return to the Village;
        all other warriors attack. Farmers in the Cave return to the Village.
    """

    MAX_WARRIOR_SPAWNS = 4
    MAX_FARMER_SPAWNS = 1
    EAT_THRESHOLD = 2        # eat when steps_since_meal >= this in the Village
    CAVE_RETURN_THRESHOLD = 4  # leave the Cave to eat when steps_since_meal >= this
    CAVE_SAFE_THRESHOLD = 2  # only send warriors to the Cave if steps_since_meal <= this

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        n = len(components)
        plan = [None] * n
        wheat_budget = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1) Feed villagers who are getting hungry.
        for i, c in enumerate(components):
            if c.steps_since_meal >= self.EAT_THRESHOLD and wheat_budget >= 1:
                plan[i] = "eat"
                wheat_budget -= 1

        # Helper to pick unassigned villagers of a given role.
        def free_indices(role=None):
            return [i for i, c in enumerate(components)
                    if plan[i] is None and (role is None or c.role == role)]

        # 2) Spawn warriors (priority: they deal the damage).
        if self.warriors_spawned < self.MAX_WARRIOR_SPAWNS and wheat_budget >= 12:
            spawners = free_indices("Farmer")[:2]
            if len(spawners) < 2:
                spawners = free_indices()[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn warrior"
                wheat_budget -= 12
                self.warriors_spawned += 1

        # 3) Spawn one farmer for wheat income.
        if self.farmers_spawned < self.MAX_FARMER_SPAWNS and wheat_budget >= 10:
            spawners = free_indices("Farmer")[:2]
            if len(spawners) == 2:
                for i in spawners:
                    plan[i] = "spawn farmer"
                wheat_budget -= 10
                self.farmers_spawned += 1

        # 4) Fed warriors go to the Cave to attack.
        for i, c in enumerate(components):
            if plan[i] is None and c.role == "Warrior":
                if dragon_alive and c.steps_since_meal <= self.CAVE_SAFE_THRESHOLD:
                    plan[i] = "cave"

        # 5) Everyone else keeps farming.
        for i in range(n):
            if plan[i] is None:
                plan[i] = "farm"

        for c, g in zip(components, plan):
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers are not meant to fight; send them home.
                group = "village"
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Warrior must eat before it starves.
                group = "village"
            else:
                group = "attack"
            environment.assign_group(c, group)