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
        assigned_ids = set()
        for c in warriors:
            environment.assign_group(c, 'cave')
            assigned_ids.add(id(c))

        # Step 2: Partition Farmers into non-overlapping final groups using wheat
        # Read current wheat in the Farm (default 0 if farm not present)
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        # Compute spawn counts deterministically (non-overlapping)
        unassigned = farmers  # list of all farmers
        spawn_farm_count = 0
        if len(unassigned) >= 2 and local_wheat >= 10:
            spawn_farm_count = min(len(unassigned) // 2, local_wheat // 10)

        # Allocate farmers to spawn farmer
        spawn_farm = []
        idx = 0
        for _ in range(spawn_farm_count):
            a = unassigned[idx]
            b = unassigned[idx + 1]
            spawn_farm.extend([a, b])
            assigned_ids.add(id(a))
            assigned_ids.add(id(b))
            idx += 2

        # Wheat left after spawning farmers
        wheat_left = local_wheat - (spawn_farm_count * 10)

        # Allocate farmers to spawn warrior from the remaining pool
        remaining_after_farm = unassigned[idx:]
        spawn_warrior_count = 0
        if len(remaining_after_farm) >= 2 and wheat_left >= 12:
            spawn_warrior_count = min(len(remaining_after_farm) // 2, wheat_left // 12)

        spawn_warrior = []
        for j in range(spawn_warrior_count):
            a = remaining_after_farm[2 * j]
            b = remaining_after_farm[2 * j + 1]
            spawn_warrior.extend([a, b])
            assigned_ids.add(id(a))
            assigned_ids.add(id(b))

        # Remaining farmers go to farming
        rest_to_farm = []
        # Collect any farmer not yet assigned
        for f in farmers:
            if id(f) not in assigned_ids:
                rest_to_farm.append(f)

        # Step 3: Apply final non-overlapping assignments
        for c in spawn_farm:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior:
            environment.assign_group(c, 'spawn warrior')
        for c in rest_to_farm:
            environment.assign_group(c, 'farm')

        # Note: Warriors are already moved to 'cave'. Farmers default to 'farm' unless assigned to spawn groups.

        # Optional: adjust wheat in farm to reflect consumption, if possible
        if farm_obj is not None and hasattr(farm_obj, 'wheat'):
            consumed = spawn_farm_count * 10 + spawn_warrior_count * 12
            new_wheat = max(0, local_wheat - consumed)
            try:
                farm_obj.wheat = new_wheat
            except Exception:
                pass  # If farm wheat can't be directly set, ignore

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