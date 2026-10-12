from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Strategy:
        # - Move all existing Warriors to the Cave (to go attack)
        # - Farmers stay in Village, but some may be allocated to spawn groups
        #   to spawn new Farmers/Warriors depending on wheat availability.

        # Move all Warriors to the Cave (they will travel to the Cave)
        for w in warriors:
            environment.assign_group(w, 'cave')

        # Spawn planning using Farmers in the Village
        available_wheat = getattr(environment.farm, 'wheat', 0)

        # Number of spawns for Farmers (2 farmers per spawn, cost 10 wheat)
        spawn_farmers = min(len(farmers) // 2, available_wheat // 10)

        # Assign 2*spawn_farmers farmers to the "spawn farmer" group
        to_spawn_farmers = farmers[:spawn_farmers * 2]
        for f in to_spawn_farmers:
            environment.assign_group(f, 'spawn farmer')

        # Remaining farmers after farming spawns
        remaining_farmers = farmers[spawn_farmers * 2:]

        # Wheat left after farmer spawns
        wheat_after_farm_spawns = max(0, available_wheat - spawn_farmers * 10)

        # Number of spawns for Warriors (2 villagers per spawn, cost 12 wheat)
        spawn_warriors = min(len(remaining_farmers) // 2, wheat_after_farm_spawns // 12)

        # Assign 2*spawn_warriors farmers to the "spawn warrior" group
        to_spawn_warriors = remaining_farmers[:spawn_warriors * 2]
        for f in to_spawn_warriors:
            environment.assign_group(f, 'spawn warrior')

        # Remaining farmers after warrior spawns
        after_warrior_spawns = remaining_farmers[spawn_warriors * 2:]

        # Everyone else (leftover farmers) stay in Village as regular farmers
        for f in after_warrior_spawns:
            environment.assign_group(f, 'farm')

        # Note: Any farmers not explicitly assigned above should be explicitly assigned.
        # If some farmers were not in the initial list due to edge cases, there is nothing else to do.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, we want Warriors to attack and Farmers to go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers should return to Village
                environment.assign_group(c, 'village')