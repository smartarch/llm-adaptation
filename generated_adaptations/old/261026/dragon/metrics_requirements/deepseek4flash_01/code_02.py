from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawns = 0
        self.warrior_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        
        # Send all warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        F = len(farmers)
        wheat = environment.farm.wheat
        
        # Determine how many spawn pairs we can afford without crippling farming
        if F >= 4:
            max_pairs = (F - 2) // 2
        elif F >= 2:
            max_pairs = F // 2
        else:
            max_pairs = 0
        
        num_farmer_spawns = 0
        num_warrior_spawns = 0
        wheat_left = wheat
        
        for _ in range(max_pairs):
            # Prioritize farmers until we have at least 6 farmers
            if F + num_farmer_spawns < 6 and wheat_left >= 10:
                num_farmer_spawns += 1
                wheat_left -= 10
            elif wheat_left >= 12:
                num_warrior_spawns += 1
                wheat_left -= 12
            elif wheat_left >= 10:
                num_farmer_spawns += 1
                wheat_left -= 10
            else:
                break
        
        # Assign farmers to appropriate groups
        idx = 0
        for _ in range(num_farmer_spawns):
            if idx + 1 < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                environment.assign_group(farmers[idx + 1], "spawn farmer")
                idx += 2
        for _ in range(num_warrior_spawns):
            if idx + 1 < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                environment.assign_group(farmers[idx + 1], "spawn warrior")
                idx += 2
        for i in range(idx, F):
            environment.assign_group(farmers[i], "farm")
        
        self.farmer_spawns += num_farmer_spawns
        self.warrior_spawns += num_warrior_spawns

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")