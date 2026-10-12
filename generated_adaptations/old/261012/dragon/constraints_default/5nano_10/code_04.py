from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) Send all Warriors to the cave (they’ll attack in assign_in_cave)
        for w in warriors:
            environment.assign_group(w, 'cave')

        total_farmers = len(farmers)

        # Wheat currently available in the Farm
        wheat_amount = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # 2) Spawn Warriors first if resources allow
        # Each warrior spawn needs 2 farmers and 12 wheat
        s_w = min(total_farmers // 2, wheat_amount // 12)

        remaining_farmers_after_warriors = total_farmers - 2 * s_w
        remaining_wheat_after_warriors = wheat_amount - 12 * s_w

        # 3) Spawn Farmers with remaining resources
        # Each farmer spawn needs 2 farmers and 10 wheat
        s_f = min(remaining_farmers_after_warriors // 2, remaining_wheat_after_warriors // 10)

        idx = 0
        # Assign 2*s_w farmers to "spawn warrior"
        for i in range(2 * s_w):
            environment.assign_group(farmers[i], 'spawn warrior')
        idx += 2 * s_w

        # Assign 2*s_f farmers to "spawn farmer"
        for i in range(2 * s_f):
            environment.assign_group(farmers[idx + i], 'spawn farmer')
        idx += 2 * s_f

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