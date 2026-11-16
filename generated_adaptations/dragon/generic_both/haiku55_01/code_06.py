from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Early game (step < 10): spare wheat goes to farmer spawns to grow the wheat
      income (a farmer yields 5 wheat per step).
    - Late game: spare wheat goes to warrior spawns (warriors deal the damage).
    - No spawns after step 18, since new villagers would arrive too late.
    - Warriors eat at >= 3 steps without a meal (they need time to walk back).
      Farmers never leave the Village, so they eat at >= 4 steps, saving wheat.
    - Fed warriors attack the Dragon from the Cave; hungry warriors return to eat.
    - Every component receives exactly one group assignment per phase.
    """

    WARRIOR_EAT_THRESHOLD = 3
    FARMER_EAT_THRESHOLD = 4
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    FARMER_PHASE_END = 10
    SPAWN_CUTOFF = 18

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _is_hungry(self, c):
        if c.role == "Warrior":
            return c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
        return c.steps_since_meal >= self.FARMER_EAT_THRESHOLD

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        hungry = [c for c in components if self._is_hungry(c)]
        fed = [c for c in components if not self._is_hungry(c)]

        # Feed the most hungry villagers first, but never more than the wheat allows.
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eating = hungry[:wheat]
        unfed = hungry[wheat:]
        wheat_avail = wheat - len(eating)

        groups = {}
        for c in eating:
            groups[c] = "eat"
        # Hungry villagers that cannot be fed stay in the Village.
        for c in unfed:
            groups[c] = "farm"

        warriors_ready = [c for c in fed if c.role == "Warrior"]
        farmers_ready = [c for c in fed if c.role != "Warrior"]

        # Fed warriors attack from the Cave.
        for c in warriors_ready:
            groups[c] = "cave"

        # Spawning: farmers first early on (economy), warriors later (damage).
        pool = list(farmers_ready)
        spawn_allowed = step <= self.SPAWN_CUTOFF

        while spawn_allowed and len(pool) >= 2:
            if step < self.FARMER_PHASE_END:
                # Economy phase: invest in farmers if affordable, else wait.
                if wheat_avail >= self.FARMER_SPAWN_COST:
                    kind, cost = "spawn farmer", self.FARMER_SPAWN_COST
                else:
                    break
            else:
                # Damage phase: warriors if affordable, otherwise farmers.
                if wheat_avail >= self.WARRIOR_SPAWN_COST:
                    kind, cost = "spawn warrior", self.WARRIOR_SPAWN_COST
                elif wheat_avail >= self.FARMER_SPAWN_COST:
                    kind, cost = "spawn farmer", self.FARMER_SPAWN_COST
                else:
                    break

            for c in pool[:2]:
                groups[c] = kind
            pool = pool[2:]
            wheat_avail -= cost

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
            elif c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD:
                # Hungry warriors return to the Village to eat in time.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")