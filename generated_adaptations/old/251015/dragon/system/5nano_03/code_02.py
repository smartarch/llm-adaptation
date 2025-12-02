from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by current role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Wheat available for spawning
        wheat = 0
        farm = getattr(environment, 'farm', None)
        if farm is not None:
            wheat = getattr(farm, 'wheat', 0)

        F = len(farmers)

        # Determine possible spawns:
        spawns_f = min(F // 2, wheat // 10)  # number of new Farmers to spawn
        wheat_remaining = wheat - spawns_f * 10

        spawns_w = min((F - 2 * spawns_f) // 2, wheat_remaining // 12)  # number of new Warriors to spawn

        # Assign 2*spawns_f farmers to "spawn farmer"
        idx = 0
        for _ in range(2 * spawns_f):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn farmer')
                idx += 1

        # Assign 2*spawns_w farmers to "spawn warrior"
        for _ in range(2 * spawns_w):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn warrior')
                idx += 1

        # Remaining farmers go to "farm"
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], 'farm')

        # All Warriors go to the Cave (to be in Cave by next step)
        for w in warriors:
            environment.assign_group(w, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack; send others back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')