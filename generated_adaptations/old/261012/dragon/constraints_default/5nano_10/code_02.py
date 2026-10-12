from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) Send all Warriors to the cave (they will attack in assign_in_cave)
        for w in warriors:
            environment.assign_group(w, 'cave')

        total_farmers = len(farmers)
        wheat = 0
        if hasattr(environment, 'farm') and hasattr(environment.farm, 'wheat'):
            wheat = environment.farm.wheat

        # 2) Decide spawns for farmers
        # Max spawns for farmers given 2 farmers per spawn and 10 wheat per spawn
        s_f = min(total_farmers // 2, wheat // 10)

        # Remaining farmers and wheat after allocating to spawn farmer group
        remaining_farmers = total_farmers - 2 * s_f
        remaining_wheat = wheat - 10 * s_f

        # Max spawns for warriors using remaining resources
        s_w = min(remaining_farmers // 2, remaining_wheat // 12)

        # 3) Assign specific farmers to spawn groups
        idx = 0
        # 2*s_f farmers to "spawn farmer"
        for i in range(2 * s_f):
            environment.assign_group(farmers[i], 'spawn farmer')
        idx += 2 * s_f

        # 2*s_w farmers to "spawn warrior"
        for i in range(s_w * 2):
            environment.assign_group(farmers[idx + i], 'spawn warrior')
        idx += s_w * 2

        # Remaining farmers go to "farm"
        for i in range(idx, total_farmers):
            environment.assign_group(farmers[i], 'farm')

        # Note: Warriors have already been moved to the cave above.
        # Farmers not assigned to spawn groups are assigned to farm below.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors attack; Farmers go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')