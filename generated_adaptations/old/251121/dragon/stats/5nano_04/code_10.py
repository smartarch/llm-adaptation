from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) != 'Farmer']

        # 1) All Warriors go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, 'cave')

        # 2) Village actions for Farmers
        F = len(farmers)
        # Reserve up to 4 farmers for farming to keep wheat flowing (adjustable)
        reserved_for_farm = min(4, F)

        # Remaining farmers available for spawning decisions
        remaining = farmers[reserved_for_farm:]

        # Wheat available in the Farm
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        i = 0
        # Spawn Warrior pairs: allow up to 2 pairs in early steps, then at most 1 pair
        max_warrior_spawns = 2 if step < 4 else 1
        spawned_warrior_pairs = 0
        while spawned_warrior_pairs < max_warrior_spawns and i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2
            spawned_warrior_pairs += 1

        # Spawn Farmer pairs after Warrior spawning opportunities are used (early steps)
        max_farmer_spawns = 1 if step < 5 else 0
        spawned_farmer_pairs = 0
        while spawned_farmer_pairs < max_farmer_spawns and i + 1 < len(remaining) and wheat >= 10:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
            wheat -= 10
            i += 2
            spawned_farmer_pairs += 1

        # Any leftover farmers go to farming
        while i < len(remaining):
            environment.assign_group(remaining[i], 'farm')
            i += 1

        # Ensure reserved farming farmers are farming
        for idx in range(reserved_for_farm):
            environment.assign_group(farmers[idx], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers should go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')