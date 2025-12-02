from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - 'farm': stay in village and farm
        - 'cave': go to the cave ( Warriors will be moved here; will attack in cave step)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Partition Farmers into non-overlapping final groups
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        spawn_farm_candidates = []
        remaining = farmers

        # Try to spawn farmers if resources allow
        if len(farmers) >= 4 and local_wheat >= 20:
            spawn_farm_candidates = farmers[:4]
            remaining = farmers[4:]
        elif len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_candidates = farmers[:2]
            remaining = farmers[2:]

        # Try to spawn warriors from remaining if resources allow
        spawn_warrior_candidates = []
        if len(remaining) >= 2 and local_wheat >= 12:
            spawn_warrior_candidates = remaining[:2]
            remaining = remaining[2:]

        rest_to_farm = remaining  # the rest stay in Farm

        # Step 4: Apply final non-overlapping assignments
        for c in spawn_farm_candidates:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_candidates:
            environment.assign_group(c, 'spawn warrior')
        for c in rest_to_farm:
            environment.assign_group(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - 'attack': Attack the Dragon
        - 'cave': Stay in the Cave
        - 'village': Go to the Village
        """
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')