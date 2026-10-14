from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack the Dragon every step.
    Farmers stay in the Village: a pair breeds Farmers, another pair breeds
    Warriors (when wheat allows), and the rest keep farming.
    All components are reassigned every step so no one drifts into a wrong group.
    """

    FARM = "farm"
    CAVE = "cave"
    SPAWN_FARMER = "spawn farmer"
    SPAWN_WARRIOR = "spawn warrior"
    ATTACK = "attack"
    VILLAGE = "village"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, self.CAVE)

        wheat = environment.farm.wheat

        # Farmers: breeding pairs if we have enough farmers, the rest farm.
        spawn_farmer_group = []
        spawn_warrior_group = []
        if len(farmers) >= 4 and wheat >= 10:
            spawn_farmer_group = farmers[0:2]
            spawn_warrior_group = farmers[2:4]
            remaining = farmers[4:]
        else:
            remaining = farmers

        for f in spawn_farmer_group:
            environment.assign_group(f, self.SPAWN_FARMER)
        for f in spawn_warrior_group:
            environment.assign_group(f, self.SPAWN_WARRIOR)
        for f in remaining:
            environment.assign_group(f, self.FARM)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking the Dragon.
                environment.assign_group(c, self.ATTACK)
            else:
                # Farmers should not be in the Cave; send them home.
                environment.assign_group(c, self.VILLAGE)