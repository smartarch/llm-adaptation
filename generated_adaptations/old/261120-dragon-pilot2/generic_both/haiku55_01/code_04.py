from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers that have not eaten for >= 3 steps are sent to eat, but only as many
      as the available wheat can pay for (most hungry first).
    - Fed warriors go to the Cave and attack the Dragon.
    - Fed farmers are used to spawn new villagers (warriors first, then farmers) with
      the wheat left after meals; the remaining farmers farm.
    - In the Cave, fed warriors attack; hungry warriors return to the Village to eat.
      Farmers in the Cave are sent back to the Village.
    - Every component receives exactly one group assignment per phase.
    """

    EAT_THRESHOLD = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        hungry = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD]
        fed = [c for c in components if c.steps_since_meal < self.EAT_THRESHOLD]

        # Feed the most hungry villagers first, but never more than the wheat allows.
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eating = hungry[:max(wheat, 0)]
        unfed = hungry[max(wheat, 0):]
        wheat_avail = wheat - len(eating)

        groups = {}
        for c in eating:
            groups[c] = "eat"

        # Unfed hungry villagers cannot eat this step; keep them in the Village.
        for c in unfed:
            groups[c] = "farm"

        warriors_ready = [c for c in fed if c.role == "Warrior"]
        farmers_ready = [c for c in fed if c.role != "Warrior"]

        # Fed warriors go to the Cave to attack.
        for c in warriors_ready:
            groups[c] = "cave"

        # Spawning consumes fed farmers as inputs, warriors first.
        pool = list(farmers_ready)

        if wheat_avail >= self.WARRIOR_SPAWN_COST and len(pool) >= 2:
            for c in pool[:2]:
                groups[c] = "spawn warrior"
            pool = pool[2:]
            wheat_avail -= self.WARRIOR_SPAWN_COST

        while wheat_avail >= self.FARMER_SPAWN_COST and len(pool) >= 2:
            for c in pool[:2]:
                groups[c] = "spawn farmer"
            pool = pool[2:]
            wheat_avail -= self.FARMER_SPAWN_COST

        # Remaining fed farmers keep farming.
        for c in pool:
            groups[c] = "farm"

        # Assign every component exactly once.
        for c in components:
            environment.assign_group(c, groups[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior":
                # Farmers should not be in the Cave.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.EAT_THRESHOLD:
                # Hungry warriors must go back to eat in time.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")