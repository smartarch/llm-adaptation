from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Build phase: warriors attack from the start, farmers spawn new warriors
    (and a few farmers) whenever wheat allows.
    Finish phase: when the Dragon is nearly dead or time is running out,
    farmers join the attack as well.
    """

    SPAWN_GROUP_SIZE = 2
    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10
    MAX_FARMER_SPAWNS = 2
    FINISH_STEP = 18
    FINISH_DRAGON_HP = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0

    def _finish_phase(self, environment, step):
        return step >= self.FINISH_STEP or environment.dragon.hp <= self.FINISH_DRAGON_HP

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors always go to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # In the finish phase farmers also go to attack; no more spawning.
        if self._finish_phase(environment, step):
            for f in farmers:
                environment.assign_group(f, "cave")
            return

        wheat = environment.farm.wheat
        pool = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Warrior spawn has priority: warriors do the damage.
        if wheat >= self.WARRIOR_WHEAT_COST and len(pool) >= self.SPAWN_GROUP_SIZE:
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_warrior_group.append(pool.pop())
            wheat -= self.WARRIOR_WHEAT_COST

        # A few farmer spawns to meet the farmer-growth requirement.
        if (self.farmers_spawned < self.MAX_FARMER_SPAWNS
                and wheat >= self.FARMER_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE):
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
        finish = self._finish_phase(environment, step)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif finish:
                environment.assign_group(c, "attack")
            else:
                # Early on, farmers are kept out of the Cave to protect wheat income.
                environment.assign_group(c, "village")