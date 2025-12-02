from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # 2) Farmers stay in the Village by default (farm)
        # Attempt to spawn new villagers using the spawn groups, constrained by wheat.
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn plan
        # - Farmer spawns: up to 3, 10 wheat each, requires 2 farmers per spawn
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_people = len(farmers) // 2
        spawn_farmers = int(min(3, max_farm_spawns_by_wheat, max_farm_spawns_by_people))

        # Allocate 2*spawn_farmers farmers to the "spawn farmer" group
        assigned_to_spawn_farm = farmers[:spawn_farmers * 2]
        for f in assigned_to_spawn_farm:
            environment.assign_group(f, 'spawn farmer')

        remaining_farmers = farmers[spawn_farmers * 2:]

        # - Warrior spawns: up to 2, 12 wheat each, requires 2 farmers per spawn
        max_war_spawns_by_wheat = wheat // 12
        max_war_spawns_by_people = len(remaining_farmers) // 2
        spawn_warriors = int(min(2, max_war_spawns_by_wheat, max_war_spawns_by_people))

        assigned_to_spawn_warrior = remaining_farmers[:spawn_warriors * 2]
        for f in assigned_to_spawn_warrior:
            environment.assign_group(f, 'spawn warrior')

        remaining_farmers_after_spawns = remaining_farmers[spawn_warriors * 2:]

        # The rest of farmers go to farming in the village
        for f in remaining_farmers_after_spawns:
            environment.assign_group(f, 'farm')

        # Note: Any other villagers that are not Farmers/Warriors should be left in their default state.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to village.
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers return to the village
                environment.assign_group(c, 'village')