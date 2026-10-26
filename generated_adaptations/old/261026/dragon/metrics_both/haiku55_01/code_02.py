from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Warriors go to the Cave to attack.
      - Farmers are split: two farmers form a "spawn farmer" pair (up to 2 times),
        two farmers form a "spawn warrior" pair (up to 2 times), and the rest farm.
    Cave:
      - Warriors attack the Dragon every step.
      - Any farmer found in the Cave returns to the Village.
    """

    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12
    MAX_SPAWN_PAIRS_PER_ROLE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawn_farmer_pairs_issued = 0
        self.spawn_warrior_pairs_issued = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide how many farmer pairs can be used for spawning this step.
        remaining = list(farmers)

        # Spawn a new Farmer if affordable and still needed.
        if (len(remaining) >= 2
                and wheat >= self.FARMER_SPAWN_COST
                and self.spawn_farmer_pairs_issued < self.MAX_SPAWN_PAIRS_PER_ROLE):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn farmer")
            remaining = remaining[2:]
            self.spawn_farmer_pairs_issued += 1

        # Spawn a new Warrior if affordable and still needed.
        if (len(remaining) >= 2
                and wheat >= self.WARRIOR_SPAWN_COST
                and self.spawn_warrior_pairs_issued < self.MAX_SPAWN_PAIRS_PER_ROLE):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn warrior")
            remaining = remaining[2:]
            self.spawn_warrior_pairs_issued += 1

        # All other farmers keep farming.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers must never stay in the Cave.
                environment.assign_group(c, "village")