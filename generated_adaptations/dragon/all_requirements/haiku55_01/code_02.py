from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - All warriors go to the Cave and attack the Dragon every step.
    - Farmers stay in the Village on the farm.
    - Wheat is used to spawn new warriors (preferred, 12 wheat) and farmers
      (10 wheat), each from pairs of farmers, while keeping a minimum
      number of farmers working the farm.
    """

    MIN_FARMERS_ON_FARM = 2
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always go to the Cave to fight the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: decide how many can be used for spawning.
        spawn_warrior = []
        spawn_farmer = []
        available = list(farmers)

        # Spawn warriors first (more damage), needs a pair of farmers and 12 wheat.
        if (wheat >= self.WARRIOR_SPAWN_COST
                and len(available) - 2 >= self.MIN_FARMERS_ON_FARM):
            spawn_warrior = available[:2]
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Then spawn farmers with the remaining wheat, keeping a farming reserve.
        if (wheat >= self.FARMER_SPAWN_COST
                and len(available) - 2 >= self.MIN_FARMERS_ON_FARM):
            spawn_farmer = available[:2]
            available = available[2:]
            wheat -= self.FARMER_SPAWN_COST

        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Every warrior in the Cave keeps attacking the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers should not stay in the Cave.
                environment.assign_group(c, "village")