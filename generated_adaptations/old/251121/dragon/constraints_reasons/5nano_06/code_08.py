from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - 'farm': stay in village and farm
        - 'cave': go to the cave (Warriors will be moved here; will attack in cave step)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Partition Farmers into non-overlapping final groups using wheat
        unassigned_farmers = list(farmers)

        # Read current wheat in the Farm (default 0 if farm not present)
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        # Spawn count calculations (non-overlapping, based on available wheat)
        spawn_farm_count = 0
        if len(unassigned_farmers) >= 2 and local_wheat >= 10:
            spawn_farm_count = min(len(unassigned_farmers) // 2, local_wheat // 10)

        to_spawn_farm = unassigned_farmers[:spawn_farm_count * 2]
        for c in to_spawn_farm:
            environment.assign_group(c, 'spawn farmer')
        unassigned_farmers = unassigned_farmers[spawn_farm_count * 2:]

        wheat_left = local_wheat - (spawn_farm_count * 10)

        spawn_warrior_count = 0
        if len(unassigned_farmers) >= 2 and wheat_left >= 12:
            spawn_warrior_count = min(len(unassigned_farmers) // 2, wheat_left // 12)

        to_spawn_warrior = unassigned_farmers[:spawn_warrior_count * 2]
        for c in to_spawn_warrior:
            environment.assign_group(c, 'spawn warrior')
        unassigned_farmers = unassigned_farmers[spawn_warrior_count * 2:]

        # Remaining farmers go to farming
        for c in unassigned_farmers:
            environment.assign_group(c, 'farm')

        # Note: Warriors were already moved to 'cave'. Farmers default to 'farm' unless assigned to spawn groups.

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