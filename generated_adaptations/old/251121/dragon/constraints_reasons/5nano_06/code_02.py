from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - 'farm': stay in village and farm
        - 'cave': go to the cave (we'll move Warriors here; in cave step they attack)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Farms stay in Village by default; we'll also attempt to spawn
        # Use a simple heuristic to allocate some farmers to spawn groups depending on wheat.
        local_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        spawn_farm_group = []
        spawn_warrior_group = []
        farm_group = []

        # Decide spawn farmer group
        if len(farmers) >= 4 and local_wheat >= 20:
            spawn_farm_group = farmers[:4]
            index = 4
        elif len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_group = farmers[:2]
            index = 2
        else:
            spawn_farm_group = []
            index = 0

        # Decide spawn warrior group from remaining farmers (to satisfy "spawn warrior" constraint)
        remaining_after_farm = farmers[index:]
        if len(remaining_after_farm) >= 2 and local_wheat >= 12:
            spawn_warrior_group = remaining_after_farm[:2]
            index += 2
        else:
            spawn_warrior_group = []

        # Rest go to farming
        farm_group = farmers[index:]

        # Apply group assignments
        for c in spawn_farm_group:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_group:
            environment.assign_group(c, 'spawn warrior')
        for c in farm_group:
            environment.assign_group(c, 'farm')

        # Note: Warriors were already moved to 'cave'. Any Farmers not in spawn groups default to 'farm'.
        # The spawn groups will trigger new villagers in the environment (as per game rules).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - 'attack': Warriors attack the Dragon
        - 'cave': stay in the Cave (not used by this strategy for Warriors)
        - 'village': go back to Village (Farmers primarily)
        """
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers (and any other non-warrior) go back to Village
                environment.assign_group(c, 'village')