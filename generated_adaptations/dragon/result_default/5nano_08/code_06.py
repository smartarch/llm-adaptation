from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All Warriors go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn strategy based on step
        initial_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        if step < 12:
            # Early game: prioritize spawning Warriors first
            max_war_spawns = min(initial_wheat // 12, len(farmers) // 2)
            if max_war_spawns > 0:
                to_spawn_war = farmers[:2 * max_war_spawns]
                for c in to_spawn_war:
                    environment.assign_group(c, "spawn warrior")

            remaining_farmers = farmers[2 * max_war_spawns:]
            wheat_after_war_spawns = initial_wheat - max_war_spawns * 12

            # Then spawn Farmers with remaining wheat
            max_farm_spawns = min(wheat_after_war_spawns // 10, len(remaining_farmers) // 2)
            if max_farm_spawns > 0:
                to_spawn_farm = remaining_farmers[:2 * max_farm_spawns]
                for c in to_spawn_farm:
                    environment.assign_group(c, "spawn farmer")

            remaining_after_spawns = remaining_farmers[2 * max_farm_spawns:]
            for c in remaining_after_spawns:
                environment.assign_group(c, "farm")
        else:
            # Later game: fall back to balanced approach
            max_farm_spawns = min(initial_wheat // 10, len(farmers) // 2)
            if max_farm_spawns > 0:
                to_spawn_farm = farmers[:2 * max_farm_spawns]
                for c in to_spawn_farm:
                    environment.assign_group(c, "spawn farmer")

            remaining_farmers2 = farmers[2 * max_farm_spawns:]
            wheat_after_farm = initial_wheat - max_farm_spawns * 10

            max_war_spawns = min(wheat_after_farm // 12, len(remaining_farmers2) // 2)
            if max_war_spawns > 0:
                to_spawn_war = remaining_farmers2[:2 * max_war_spawns]
                for c in to_spawn_war:
                    environment.assign_group(c, "spawn warrior")

            remaining_after_war = remaining_farmers2[2 * max_war_spawns:]
            for c in remaining_after_war:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")