from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Build a target group mapping for all villagers
        target = {}

        # Warriors should go to the cave
        for w in warriors:
            target[w] = 'cave'

        # Farmers default to farming in the village
        for f in farmers:
            target[f] = 'farm'

        # Access wheat (if available)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farming farmers: up to 3, requires 2 farmers and 10 wheat
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_people = len(farmers) // 2
        spawn_farmers = int(min(3, max_farm_spawns_by_wheat, max_farm_spawns_by_people))

        # Override first 2*spawn_farmers farmers to spawn farmer
        if spawn_farmers > 0:
            for i in range(spawn_farmers * 2):
                if i < len(farmers):
                    target[farmers[i]] = 'spawn farmer'

        # Spawn warrior farmers: requires two farmers per spawn and 12 wheat
        remaining_farmers = farmers[spawn_farmers * 2:]
        max_war_spawns_by_wheat = wheat // 12
        max_war_spawns_by_people = len(remaining_farmers) // 2
        spawn_warriors = int(min(2, max_war_spawns_by_wheat, max_war_spawns_by_people))

        if spawn_warriors > 0:
            for i in range(spawn_warriors * 2):
                if i < len(remaining_farmers):
                    target[remaining_farmers[i]] = 'spawn warrior'

        # Apply assignments for all mapped villagers
        assigned = set()
        for c, g in target.items():
            environment.assign_group(c, g)
            assigned.add(c)

        # Fallback: assign any unmapped components to a safe default
        for c in components:
            if c not in assigned:
                environment.assign_group(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack, Farmers go to village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')