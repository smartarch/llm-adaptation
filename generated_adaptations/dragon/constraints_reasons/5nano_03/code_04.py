from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the Village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors_in_village = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Move all Warriors currently in the Village to the Cave
        for w in warriors_in_village:
            environment.assign_group(w, 'cave')

        # Count available resources in the Village
        F = len(farmers)
        W = getattr(environment.farm, 'wheat', 0)

        # Compute the best (sf, sw) spawn plan given constraints
        best_spawns = -1
        best_sf = 0
        best_sw = 0
        # sf ranges from 0..F//2
        for sf in range(0, (F // 2) + 1):
            # Remaining villagers after using sf spawns
            remaining_villagers = F - 2 * sf
            # Max possible sw given remaining villagers and wheat
            max_sw_by_villagers = remaining_villagers // 2
            max_sw_by_wheat = (W - 10 * sf) // 12 if (W - 10 * sf) >= 0 else -1
            max_sw = min(max_sw_by_villagers, max_sw_by_wheat)
            if max_sw < 0:
                continue
            # Iterate possible sw values for this sf
            for sw in range(0, max_sw + 1):
                total = sf + sw
                if total > best_spawns:
                    best_spawns = total
                    best_sf = sf
                    best_sw = sw
                elif total == best_spawns:
                    # Prefer having at least one Warrior spawn if possible
                    if best_sw == 0 and sw > 0:
                        best_sf = sf
                        best_sw = sw

        sf = best_sf
        sw = best_sw

        # Assign farmers to spawn groups accordingly
        used_index = 0  # index in farmers list

        # Spawn farmers: 2 farmers per sf
        for _ in range(sf):
            if used_index + 1 < F:
                environment.assign_group(farmers[used_index], 'spawn farmer')
                environment.assign_group(farmers[used_index + 1], 'spawn farmer')
                used_index += 2

        # Spawn warriors: 2 farmers per sw
        for _ in range(sw):
            if used_index + 1 < F:
                environment.assign_group(farmers[used_index], 'spawn warrior')
                environment.assign_group(farmers[used_index + 1], 'spawn warrior')
                used_index += 2

        # Remaining farmers (if any) stay in the Village and farm
        for i in range(used_index, F):
            environment.assign_group(farmers[i], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, Warriors attack; Farmers return to the Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')