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

        # 2) Determine spawns based on initial wheat in Farm
        initial_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)
        num_farmers = len(farmers)

        # Farmer spawns: 2 farmers + 10 wheat -> 1 new Farmer
        max_farm_spawns = min(initial_wheat // 10, num_farmers // 2)

        # Assign 2*max_farm_spawns farmers to "spawn farmer"
        if max_farm_spawns > 0:
            to_spawn_farm = farmers[:2 * max_farm_spawns]
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")

        # Remaining wheat after farmer spawns
        remaining_wheat = initial_wheat - max_farm_spawns * 10

        # Remaining farmers after allocating to farm-spawns
        remaining_farmers_for_warriors = farmers[2 * max_farm_spawns:]

        # Warrior spawns: 2 farmers + 12 wheat -> 1 new Warrior
        max_war_spawns = min(remaining_wheat // 12, len(remaining_farmers_for_warriors) // 2)

        # Assign 2*max_war_spawns farmers to "spawn warrior"
        if max_war_spawns > 0:
            to_spawn_war = remaining_farmers_for_warriors[:2 * max_war_spawns]
            for c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")

        # Remaining farmers after spawning warriors go to farming in Village
        remaining_after_war = remaining_farmers_for_warriors[2 * max_war_spawns:]
        for c in remaining_after_war:
            environment.assign_group(c, "farm")

        # Note: Warriors were sent to cave earlier; any Farmers not used for spawning go to farming.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")