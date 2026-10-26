import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack the Dragon every step.
    Farmers stay on the farm and, when wheat allows, are temporarily
    assigned to spawn groups to create a few new Warriors and new Farmers.
    Any Farmer that ends up in the Cave is sent back to the Village.
    """

    MIN_FARMERS_FOR_SPAWNING = 3   # keep enough farmers working on the farm
    MAX_SPAWN_ATTEMPTS = 2         # attempts per spawn type (at least two of each)
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_attempts = 0
        self.farmer_spawn_attempts = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior goes to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide which farmers (if any) are used for spawning.
        spawn_warrior_group = []
        spawn_farmer_group = []
        remaining = list(farmers)

        if len(farmers) >= self.MIN_FARMERS_FOR_SPAWNING:
            # Prioritise warrior spawning (needs 2 villagers + 12 wheat).
            if (self.warrior_spawn_attempts < self.MAX_SPAWN_ATTEMPTS
                    and wheat >= self.WARRIOR_SPAWN_COST
                    and len(remaining) >= 2):
                spawn_warrior_group = remaining[:2]
                remaining = remaining[2:]
                self.warrior_spawn_attempts += 1

            # Then farmer spawning (needs 2 villagers + 10 wheat).
            if (self.farmer_spawn_attempts < self.MAX_SPAWN_ATTEMPTS
                    and wheat - (self.WARRIOR_SPAWN_COST if spawn_warrior_group else 0) >= self.FARMER_SPAWN_COST
                    and len(remaining) >= 2 + 1):  # keep at least one farmer farming
                spawn_farmer_group = remaining[:2]
                remaining = remaining[2:]
                self.farmer_spawn_attempts += 1

        # Assign spawn groups.
        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # All other farmers keep farming.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers do not fight; send them back to the Village.
                environment.assign_group(c, "village")