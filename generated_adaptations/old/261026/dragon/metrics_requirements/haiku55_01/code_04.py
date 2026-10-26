from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors attack the Dragon from step 1 and are reinforced with
    warrior spawns whenever wheat allows. Farmers keep the wheat flowing
    and a small number of farmers are spawned early.
    """

    SPAWN_GROUP_SIZE = 2
    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10
    MIN_FARMERS_LEFT_FARMING = 1
    MAX_FARMER_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = environment.farm.wheat
        pool = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Prefer warrior spawns, since warriors do the damage.
        if (wheat >= self.WARRIOR_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_LEFT_FARMING):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_warrior_group.append(pool.pop())
            wheat -= self.WARRIOR_WHEAT_COST

        # Early farmer spawns to meet the farmer-growth requirement.
        if (self.farmers_spawned < self.MAX_FARMER_SPAWNS
                and wheat >= self.FARMER_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_LEFT_FARMING):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_farmer_group.append(pool.pop())
            wheat -= self.FARMER_WHEAT_COST
            self.farmers_spawned += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers have 4 HP and deal 1 damage; keep them out of the Cave.
                environment.assign_group(c, "village")