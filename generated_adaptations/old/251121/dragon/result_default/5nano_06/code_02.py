from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in the village by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All Warriors should go to the cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # 2) Allocate farmers to farming / spawning groups based on available wheat
        wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)
        n_farmers = len(farmers)

        # Max number of warrior-spawn groups we can form from farmers given wheat
        max_war_spawns = min(n_farmers // 2, wheat // 12)
        remaining_wheat_after_war = wheat - max_war_spawns * 12

        # Max number of farmer-spawn groups we can form with remaining farmers and wheat
        max_farm_spawns = min((n_farmers - max_war_spawns * 2) // 2, remaining_wheat_after_war // 10)

        # Assign farmers to the appropriate groups:
        # - First 2*max_war_spawns farmers -> spawn warrior
        # - Next 2*max_farm_spawns farmers -> spawn farmer
        # - Remaining farmers -> farm
        for i, f in enumerate(farmers):
            if i < max_war_spawns * 2:
                environment.assign_group(f, 'spawn warrior')
            elif i < max_war_spawns * 2 + max_farm_spawns * 2:
                environment.assign_group(f, 'spawn farmer')
            else:
                environment.assign_group(f, 'farm')

        # Note: If there are no farmers, Warriors have already been sent to cave.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack the Dragon; Farmers return to Village
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')