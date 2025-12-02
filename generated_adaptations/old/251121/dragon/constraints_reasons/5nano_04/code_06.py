from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Determine roles present in the village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Build initial deterministic mapping: Warriors -> cave, Farmers -> farm
        mapping = {}
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                mapping[c] = 'cave'
            else:
                mapping[c] = 'farm'

        # Read wheat with safe access
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmers: up to 3, requires 2 farmers per spawn and 10 wheat per spawn
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_people = len(farmers) // 2
        spawn_farmers = int(min(3, max_farm_spawns_by_wheat, max_farm_spawns_by_people))

        if spawn_farmers > 0:
            # Choose 2*spawn_farmers farmers currently mapped to 'farm' to become 'spawn farmer'
            candidates = [f for f in farmers if mapping.get(f) == 'farm']
            count = 0
            for f in candidates:
                if count >= 2 * spawn_farmers:
                    break
                mapping[f] = 'spawn farmer'
                count += 1

        # Spawn warriors: requires 2 farmers for each spawn and 12 wheat per spawn
        remaining_for_warriors = [f for f in farmers if mapping.get(f) in ('farm', 'spawn farmer')]
        max_war_spawns_by_wheat = wheat // 12
        max_war_spawns_by_people = len(remaining_for_warriors) // 2
        spawn_warriors = int(min(2, max_war_spawns_by_wheat, max_war_spawns_by_people))

        if spawn_warriors > 0:
            candidates = [f for f in remaining_for_warriors if mapping.get(f) in ('farm', 'spawn farmer')]
            count = 0
            for f in candidates:
                if count >= 2 * spawn_warriors:
                    break
                mapping[f] = 'spawn warrior'
                count += 1

        # Apply final mapping to all components; ensure every component is assigned exactly once
        for c in components:
            g = mapping.get(c, 'farm')
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the Dragon; Farmers go to the Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')