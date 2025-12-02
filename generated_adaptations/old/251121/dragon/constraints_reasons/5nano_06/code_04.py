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

        # Step 2: Default: all Farmers go to Farm
        for c in farmers:
            environment.assign_group(c, 'farm')

        # Step 3: Determine spawn opportunities based on current Wheat
        local_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # Prepare non-overlapping spawn groups
        spawn_farm_candidates = []
        if len(farmers) >= 4 and local_wheat >= 20:
            spawn_farm_candidates = farmers[:4]
        elif len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_candidates = farmers[:2]

        remaining_after_farm = [f for f in farmers if f not in spawn_farm_candidates]

        spawn_warrior_candidates = []
        if len(remaining_after_farm) >= 2 and local_wheat >= 12:
            spawn_warrior_candidates = remaining_after_farm[:2]

        rest_to_farm = [f for f in farmers if f not in spawn_farm_candidates and f not in spawn_warrior_candidates]

        # Step 4: Apply final non-overlapping assignments
        for c in spawn_farm_candidates:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_candidates:
            environment.assign_group(c, 'spawn warrior')
        for c in rest_to_farm:
            environment.assign_group(c, 'farm')

        # Note: Warriors were already moved to 'cave'. Farmers defaulted to 'farm' or overridden by spawn groups.

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
                # Farmers (and any other non-warrior) go back to Village
                environment.assign_group(c, 'village')