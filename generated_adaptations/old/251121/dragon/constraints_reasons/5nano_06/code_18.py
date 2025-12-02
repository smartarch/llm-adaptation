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

        # Fetch current wheat in the Farm
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        # Step 1: Assign all Warriors to cave (non-overlapping single assignment)
        mapping = {}  # component -> group_id
        for w in warriors:
            mapping[w] = 'cave'

        # Step 2: Determine spawn opportunities from farmers using wheat, in a single pass
        # We compute two non-overlapping allocations: spawn_farm and spawn_warrior
        spawn_farm_count = 0
        if len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_count = min(len(farmers) // 2, local_wheat // 10)

        # Identify which farmers go to spawn farmer (first 2*spawn_farm_count in order)
        spawn_farm_set = set()
        idx = 0
        for _ in range(spawn_farm_count):
            a = farmers[idx]
            b = farmers[idx + 1]
            spawn_farm_set.add(a)
            spawn_farm_set.add(b)
            idx += 2

        wheat_left = local_wheat - (spawn_farm_count * 10)

        # Spawn warrior from remaining farmers if possible
        remaining_after_farm = farmers[idx:]
        spawn_warrior_count = 0
        if len(remaining_after_farm) >= 2 and wheat_left >= 12:
            spawn_warrior_count = min(len(remaining_after_farm) // 2, wheat_left // 12)

        spawn_warrior_set = set()
        for j in range(spawn_warrior_count):
            a = remaining_after_farm[2 * j]
            b = remaining_after_farm[2 * j + 1]
            spawn_warrior_set.add(a)
            spawn_warrior_set.add(b)

        # Rest of farmers go to farming
        farm_set = [f for f in farmers if f not in spawn_farm_set and f not in spawn_warrior_set]

        # Apply mappings
        for f in spawn_farm_set:
            mapping[f] = 'spawn farmer'
        for f in spawn_warrior_set:
            mapping[f] = 'spawn warrior'
        for f in farm_set:
            mapping[f] = 'farm'

        # If there are any components not yet assigned (edge-cases), assign them to farm as a safety net
        for c in components:
            if c not in mapping:
                mapping[c] = 'farm'

        # Execute assignments
        for comp, grp in mapping.items():
            environment.assign_group(comp, grp)

        # Optional: reflect wheat consumption
        if farm_obj is not None and hasattr(farm_obj, 'wheat'):
            consumed = spawn_farm_count * 10 + spawn_warrior_count * 12
            try:
                farm_obj.wheat = max(0, local_wheat - consumed)
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