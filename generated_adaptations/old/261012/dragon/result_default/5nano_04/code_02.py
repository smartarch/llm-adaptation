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

        # Handle Farmers: decide spawning vs farming
        if farmers:
            # Current wheat available at the Farm
            available_wheat = getattr(environment.farm, 'wheat', 0)
            num_farmers = len(farmers)

            # Plan spawns: each spawn event consumes 2 farmers and some wheat
            spawn_farmers_count = min(num_farmers // 2, available_wheat // 10)

            remaining_farmers_after_farmspawn = num_farmers - spawn_farmers_count * 2
            remaining_wheat_after_farmspawn = available_wheat - spawn_farmers_count * 10

            spawn_warriors_count = min(remaining_farmers_after_farmspawn // 2,
                                       remaining_wheat_after_farmspawn // 12)

            idx = 0
            # Assign to spawn farmer group
            for _ in range(spawn_farmers_count):
                environment.assign_group(farmers[idx], 'spawn farmer')
                environment.assign_group(farmers[idx + 1], 'spawn farmer')
                idx += 2

            # Assign to spawn warrior group
            for _ in range(spawn_warriors_count):
                environment.assign_group(farmers[idx], 'spawn warrior')
                environment.assign_group(farmers[idx + 1], 'spawn warrior')
                idx += 2

            # Remaining farmers go to farming in the Village
            for j in range(idx, num_farmers):
                environment.assign_group(farmers[j], 'farm')
        # If there are no farmers, Warriors have already been sent to cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')