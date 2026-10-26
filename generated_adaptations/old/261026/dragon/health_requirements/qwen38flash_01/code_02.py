from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawns = 0
        self._farmer_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.farm.wheat

        # All warriors go to the cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Determine how many farmers must stay farming (economy floor)
        if len(farmers) >= 4:
            min_farming = 2
        else:
            min_farming = 1

        available_for_spawn = max(0, len(farmers) - min_farming)

        # Decide whether to spawn this step
        spawn_group = None
        num_spawn = 0

        # Priority 1: Spawn warriors in early-mid game for damage output
        if step < 12 and wheat >= 12 and available_for_spawn >= 2 and self._warrior_spawns < 4:
            spawn_group = "spawn warrior"
            num_spawn = 2
        # Priority 2: Spawn farmers to grow wheat production (at least a few)
        elif step >= 2 and wheat >= 10 and available_for_spawn >= 2 and self._farmer_spawns < 3:
            spawn_group = "spawn farmer"
            num_spawn = 2
        # Priority 3: Later spawning if we still have excess farmers and wheat
        elif step < 22 and wheat >= 12 and available_for_spawn >= 2 and self._warrior_spawns < 6:
            spawn_group = "spawn warrior"
            num_spawn = 2

        # Assign farmers to groups
        for i, farmer in enumerate(farmers):
            if spawn_group and i < num_spawn:
                environment.assign_group(farmer, spawn_group)
            else:
                environment.assign_group(farmer, "farm")

        # Track spawns for limiting total number
        if spawn_group == "spawn warrior":
            self._warrior_spawns += 1
        elif spawn_group == "spawn farmer":
            self._farmer_spawns += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # All warriors attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Non-warriors (farmers) should return to village
                environment.assign_group(c, "village")