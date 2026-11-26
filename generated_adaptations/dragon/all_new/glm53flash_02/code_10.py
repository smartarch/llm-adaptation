from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_started = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        n_total = len(all_warriors) + len(all_farmers)
        n_warriors = len(all_warriors)
        dragon_hp = environment.dragon.hp

        enough_army = n_warriors >= 4
        final_rush = dragon_hp <= 15 and n_warriors >= 1
        attack_mode = self.attack_started or enough_army or final_rush
        if enough_army or final_rush:
            self.attack_started = True

        assigned = set()
        # 1) starving villagers eat (must eat before hitting 6)
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(c)
        remaining = [c for c in components if c not in assigned]

        # 2) warriors attack when in attack mode
        warriors_here = [c for c in remaining if c.role == "Warrior"]
        if attack_mode:
            for c in warriors_here:
                environment.assign_group(c, "cave")
                assigned.add(c)
        remaining = [c for c in remaining if c not in assigned]

        # 3) spawning with a solid wheat buffer so everyone can always eat
        reserve = 2 * n_total + 4
        can_w = wheat - 12 >= reserve
        can_f = wheat - 10 >= reserve

        spawn_w = can_w and (n_warriors < 4 or attack_mode)
        spawn_f = can_f and n_total < 6 and not (spawn_w and len(remaining) < 4)

        n_sw = 2 if (spawn_w and len(remaining) >= 2) else 0
        n_sf = 2 if (spawn_f and len(remaining) - n_sw >= 2) else 0
        if len(remaining) - n_sw - n_sf < 1:
            n_sf = max(0, len(remaining) - n_sw - 1)

        for i, c in enumerate(remaining):
            if i < n_sw:
                environment.assign_group(c, "spawn warrior")
            elif i < n_sw + n_sf:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 4:
                # travel takes one step; arriving at 5 lets them eat in time
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")