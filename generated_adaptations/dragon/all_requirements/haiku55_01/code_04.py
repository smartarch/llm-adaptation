from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors always go to the Cave and attack the Dragon.
    - Farmers are paired up and spawned into warriors (preferred, 12 wheat)
      or farmers (10 wheat) whenever wheat and population targets allow.
    - Remaining farmers keep farming, and at least one farmer stays on the
      farm whenever farmers exist, so wheat income is not fully cut off.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    TARGET_WARRIORS = 8
    TARGET_FARMERS = 8
    MAX_PAIRS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always go to the Cave to fight the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        warrior_count = len(warriors)
        farmer_count = len(farmers)

        # Simulated counts to decide how many spawns we still want.
        pool = list(farmers)
        spawn_warrior = []
        spawn_farmer = []
        pairs_done = 0

        # Prefer warrior spawns while warrior count is below target.
        while (len(pool) >= 2
               and wheat >= self.WARRIOR_SPAWN_COST
               and warrior_count < self.TARGET_WARRIORS
               and pairs_done < self.MAX_PAIRS_PER_STEP):
            spawn_warrior.extend(pool[:2])
            pool = pool[2:]
            wheat -= self.WARRIOR_SPAWN_COST
            warrior_count += 1
            pairs_done += 1

        # Then spawn farmers while farmer count is below target.
        while (len(pool) >= 2
               and wheat >= self.FARMER_SPAWN_COST
               and farmer_count < self.TARGET_FARMERS
               and pairs_done < self.MAX_PAIRS_PER_STEP):
            spawn_farmer.extend(pool[:2])
            pool = pool[2:]
            wheat -= self.FARMER_SPAWN_COST
            farmer_count += 1
            pairs_done += 1

        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Every warrior in the Cave keeps attacking the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers must not remain in the Cave.
                environment.assign_group(c, "village")