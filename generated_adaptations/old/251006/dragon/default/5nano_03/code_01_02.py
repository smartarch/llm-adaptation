from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Send all Warriors to the Cave (they will attack from there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village to farm by default
        #    We'll optionally spawn a new Farmer if resources allow.
        #    Determine wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Decide spawn plan: spawn 2 Farmers if we have at least 2 farmers
        # and at least 10 wheat (spawn Farmer cost)
        spawn_farm_count = 0
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farm_count = 2  # two farmers go to spawn farmer group to spawn one new farmer

        # Assign farmers to either "spawn farmer" or "farm"
        spawned = 0
        for f in farmers:
            if spawned < spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
                spawned += 1
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack; Farmers should go to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")