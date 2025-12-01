from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in the Village into: farm, cave, spawn farmer, spawn warrior
        # Warriors go to cave
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']

        for w in warriors:
            environment.assign_group(w, 'cave')

        # Handle Farmers: dynamic spawning prioritizing Warriors first
        if not farmers:
            return

        available_wheat = getattr(environment.farm, 'wheat', 0)
        num_farmers = len(farmers)
        idx = 0

        # First, spawn as many Warriors as possible (needs 2 farmers and 12 wheat per Warrior)
        max_warrior_spawns = min(num_farmers // 2, available_wheat // 12)

        for _ in range(max_warrior_spawns):
            environment.assign_group(farmers[idx], 'spawn warrior')
            environment.assign_group(farmers[idx + 1], 'spawn warrior')
            idx += 2

        remaining_farmers = num_farmers - idx
        remaining_wheat = available_wheat - max_warrior_spawns * 12

        # Then spawn Farmers if possible (needs 2 farmers and 10 wheat per Farmer)
        max_farmer_spawns = min(remaining_farmers // 2, remaining_wheat // 10)

        for _ in range(max_farmer_spawns):
            environment.assign_group(farmers[idx], 'spawn farmer')
            environment.assign_group(farmers[idx + 1], 'spawn farmer')
            idx += 2

        # Remaining farmers go to farming in Village
        for j in range(idx, num_farmers):
            environment.assign_group(farmers[j], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Attack with Warriors; Farmers should go to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')