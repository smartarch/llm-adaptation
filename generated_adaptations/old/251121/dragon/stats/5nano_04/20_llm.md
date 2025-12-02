```py
# Reasoning and new adaptation strategy (embedded as comments for clarity):
# - The Dragon is tough (HP 50) and retaliation in the Cave can wipe out waves of villagers.
# - A safer, slower ramp tends to preserve villagers long enough to sustain wheat production and
#   allow gradual DPS growth.
# - Core ideas implemented here:
#   1) Move at most one Warrior to the Cave per village step to avoid large casualty bursts.
#   2) Maintain a small wheat-producing core in the Village by reserving up to 3 Farmers for farming.
#   3) Spawn at most one Warrior pair per step if there are at least 2 free Farmers and at least 12 wheat.
#   4) After Warrior spawning opportunities, (optionally, early in the run) spawn at most one Farmer pair
#      per step if there are enough wheat (>=10) and enough farmers remain.
#   5) Remaining Farmers go to farming (to sustain wheat production).
#   6) In the Cave, all Warriors attack; Farmers are returned to the Village to minimize cave casualties.
# - This approach aims for a steady DPS ramp while preserving a wheat engine for future spawns,
#   with per-step limits to reduce catastrophic losses and improve survival through 30 turns.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) != 'Farmer']

        # 1) Move at most one Warrior to the Cave per step to limit casualties
        if len(warriors) > 0:
            environment.assign_group(warriors[0], 'cave')

        # 2) Village actions for Farmers
        F = len(farmers)
        # Keep a small wheat-producing core
        reserved_for_farm = min(3, F)

        # Remaining farmers available for spawning decisions
        remaining = farmers[reserved_for_farm:]

        # Wheat available in the Farm
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        i = 0
        # Spawn at most one Warrior pair per step if possible (12 wheat)
        max_warrior_spawns = 1 if (len(remaining) >= 2) and (wheat >= 12) else 0
        spawned_warrior_pairs = 0
        while spawned_warrior_pairs < max_warrior_spawns and i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2
            spawned_warrior_pairs += 1

        # Spawn at most one Farmer pair per step if possible, after Warrior spawning opportunities
        max_farmer_spawns = 1 if (step < 28) and (i + 1 < len(remaining)) and (wheat >= 10) else 0
        spawned_farmer_pairs = 0
        while spawned_farmer_pairs < max_farmer_spawns and i + 1 < len(remaining) and wheat >= 10:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
            wheat -= 10
            i += 2
            spawned_farmer_pairs += 1

        # Any leftover farmers go to farming
        while i < len(remaining):
            environment.assign_group(remaining[i], 'farm')
            i += 1

        # Ensure reserved farming farmers remain farming
        for idx in range(reserved_for_farm):
            environment.assign_group(farmers[idx], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers return to Village to minimize risk
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```