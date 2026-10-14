from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Heuristic counters for requested spawns (each type capped at 2)
        self.spawn_requests_farmer = 0
        self.spawn_requests_warrior = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to fight the dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide which spawn (if any) to perform this step.
        # Spawning needs two villagers in the spawn group, so we need >= 2 farmers.
        spawn_group_members = []
        spawn_target = None
        if len(farmers) >= 2:
            if self.spawn_requests_warrior < 2 and wheat >= 12:
                spawn_target = "spawn warrior"
                self.spawn_requests_warrior += 1
            elif self.spawn_requests_farmer < 2 and wheat >= 10:
                spawn_target = "spawn farmer"
                self.spawn_requests_farmer += 1

        if spawn_target is not None:
            spawn_group_members = farmers[:2]

        # Assign the spawn pair (if any), the rest of the farmers keep farming
        for f in farmers:
            if f in spawn_group_members:
                environment.assign_group(f, spawn_target)
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Keep attacking while healthy; retreat nearly dead warriors
                if c.hp > 1:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")
            else:
                # Farmers do not fight; they return to the village to farm
                environment.assign_group(c, "village")