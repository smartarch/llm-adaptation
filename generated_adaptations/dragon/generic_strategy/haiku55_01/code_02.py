from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors rush to the Cave and attack the Dragon from the first steps.
    Farmers stay on the farm and, when wheat allows, are paired up to spawn
    additional Warriors and Farmers (at most two spawn batches of each type).
    Warriors with very low HP retreat to the Village to survive.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_batches = 0
        self.farmer_spawn_batches = 0
        self.max_spawn_batches = 2
        self.min_hp_to_fight = 2  # warriors at or below 1 HP retreat

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the cave to attack the dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide which farmers are used for spawning.
        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Priority 1: spawn warriors (needed for damage) if wheat allows.
        if (self.warrior_spawn_batches < self.max_spawn_batches
                and wheat >= 12 and len(available) >= 2):
            spawn_warrior_group = available[:2]
            available = available[2:]
            self.warrior_spawn_batches += 1

        # Priority 2: spawn farmers if wheat allows and enough farmers remain
        # to keep at least one farmer on the farm afterwards.
        if (self.farmer_spawn_batches < self.max_spawn_batches
                and wheat >= 10 and len(available) >= 3):
            spawn_farmer_group = available[:2]
            available = available[2:]
            self.farmer_spawn_batches += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # Everyone else keeps farming.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp >= self.min_hp_to_fight:
                # Warriors with enough HP keep attacking the dragon.
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                # Badly wounded warriors retreat to heal/survive.
                environment.assign_group(c, "village")
            else:
                # Farmers are too fragile to fight; send them back to work.
                environment.assign_group(c, "village")