from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack the Dragon every step.
    Farmers stay in the Village. A wheat budget decides each step whether
    a pair of farmers breeds a Warrior (preferred while warriors are scarce)
    or a Farmer. Leftover farmers keep farming for wheat income.
    """

    FARM = "farm"
    CAVE = "cave"
    SPAWN_FARMER = "spawn farmer"
    SPAWN_WARRIOR = "spawn warrior"
    ATTACK = "attack"
    VILLAGE = "village"

    WARRIOR_TARGET = 4      # Keep breeding warriors until this many exist
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warriors_seen = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, self.CAVE)

        wheat = environment.farm.wheat
        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Count all warriors (village + cave) to decide what is scarce.
        total_warriors = len(warriors) + self._warriors_seen

        # Prefer breeding warriors while they are scarce.
        if total_warriors < self.WARRIOR_TARGET and len(available) >= 2 and wheat >= self.WARRIOR_COST:
            spawn_warrior_group = available[0:2]
            available = available[2:]
            wheat -= self.WARRIOR_COST

        # Then breed farmers if the budget allows.
        if len(available) >= 2 and wheat >= self.FARMER_COST:
            spawn_farmer_group = available[0:2]
            available = available[2:]
            wheat -= self.FARMER_COST

        # If warriors are still short and wheat remains, breed another warrior.
        if (not spawn_warrior_group and total_warriors < self.WARRIOR_TARGET
                and len(available) >= 2 and wheat >= self.WARRIOR_COST):
            spawn_warrior_group = available[0:2]
            available = available[2:]
            wheat -= self.WARRIOR_COST

        for f in spawn_warrior_group:
            environment.assign_group(f, self.SPAWN_WARRIOR)
        for f in spawn_farmer_group:
            environment.assign_group(f, self.SPAWN_FARMER)
        for f in available:
            environment.assign_group(f, self.FARM)

        self._warriors_seen = max(self._warriors_seen, len(warriors))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking the Dragon.
                environment.assign_group(c, self.ATTACK)
            else:
                # Farmers should not be in the Cave; send them home.
                environment.assign_group(c, self.VILLAGE)