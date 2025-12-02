from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups without overlaps:
        - All Warriors -> 'cave'
        - Farmers partitioned into:
          - 'spawn farmer' (pairs of farmers, cost 10 wheat per pair)
          - 'spawn warrior' (pairs of farmers, cost 12 wheat per pair)
          - 'farm' for the remaining farmers
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: Assign all Warriors to the Cave (single pass, no overlap)
        for w in warriors:
            environment.assign_group(w, 'cave')

        # Step 2: Determine wheat available in Farm
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        # Step 3: Greedily allocate Farmers to spawn groups without overlaps
        left = list(farmers)

        pairs_farm = []
        pairs_warrior = []
        wheat = local_wheat

        # Spawn farmer pairs as long as we have at least 2 farmers left and enough wheat
        while len(left) >= 2 and wheat >= 10:
            a = left.pop(0)
            b = left.pop(0)
            pairs_farm.append((a, b))
            wheat -= 10

        # Spawn warrior pairs from the remaining farmers, if enough wheat remains
        while len(left) >= 2 and wheat >= 12:
            a = left.pop(0)
            b = left.pop(0)
            pairs_warrior.append((a, b))
            wheat -= 12

        # The rest go to farming
        farm_list = list(left)

        # Step 4: Apply final non-overlapping assignments
        for a, b in pairs_farm:
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
        for a, b in pairs_warrior:
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
        for f in farm_list:
            environment.assign_group(f, 'farm')

        # Update Wheat to reflect consumption
        if farm_obj is not None and hasattr(farm_obj, 'wheat'):
            try:
                farm_obj.wheat = max(0, wheat)
            except Exception:
                pass

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