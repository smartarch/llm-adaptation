from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Wheat available for spawning
        wheat = getattr(getattr(environment, 'farm', object()), 'wheat', 0)

        # How many spawns can we support? Each spawn requires 2 villagers and 10 wheat
        spawns_potential = min(len(farmers) // 2, int(wheat // 10))

        # Choose which farmers participate in spawning
        spawn_farmers = farmers[:2 * spawns_potential]
        remaining_farmers = farmers[2 * spawns_potential:]

        # Assign groups
        for c in remaining_farmers:
            environment.assign_group(c, 'farm')

        for c in spawn_farmers:
            environment.assign_group(c, 'spawn farmer')

        # All Warriors go to the cave to attack (via the cave group in village phase)
        for c in warriors:
            environment.assign_group(c, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers and any other non-Warrior villagers go to the Village
                environment.assign_group(c, 'village')