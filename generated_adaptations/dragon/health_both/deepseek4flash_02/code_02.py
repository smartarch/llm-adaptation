from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        warriors = [c for c in components if c.role == 'Warrior']
        farmers = [c for c in components if c.role == 'Farmer']
        
        # All warriors go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        wheat = environment.farm.wheat
        num_farmers = len(farmers)
        max_pairs = num_farmers // 2
        
        # Determine how many new farmers/warriors we still need
        needed_farmers = max(0, 2 - self.spawned_farmers)
        needed_warriors = max(0, 2 - self.spawned_warriors)
        
        pairs_for_farmer = 0
        pairs_for_warrior = 0
        
        # First, try to spawn the needed farmers
        if needed_farmers > 0 and max_pairs > 0:
            affordable = wheat // 10
            take = min(needed_farmers, max_pairs, affordable)
            pairs_for_farmer = take
            wheat -= take * 10
            max_pairs -= take
        
        # Then, try to spawn the needed warriors
        if needed_warriors > 0 and max_pairs > 0:
            affordable = wheat // 12
            take = min(needed_warriors, max_pairs, affordable)
            pairs_for_warrior = take
            wheat -= take * 12
            max_pairs -= take
        
        # Any remaining capacity goes to spawning more warriors (for damage)
        if max_pairs > 0:
            affordable = wheat // 12
            take = min(max_pairs, affordable)
            pairs_for_warrior += take
            wheat -= take * 12
            max_pairs -= take
        
        # Assign farmers to spawn groups and the farm
        idx = 0
        for _ in range(2 * pairs_for_farmer):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        for _ in range(2 * pairs_for_warrior):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        for i in range(idx, num_farmers):
            environment.assign_group(farmers[i], "farm")
        
        # Update spawn counters
        self.spawned_farmers += pairs_for_farmer
        self.spawned_warriors += pairs_for_warrior

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the dragon, farmers go back to the village
        for c in components:
            if c.role == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")