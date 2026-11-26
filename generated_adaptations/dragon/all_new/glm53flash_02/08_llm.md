Two problems: (1) wheat ran out because my reserve (1 meal/villager) didn't account for all the eaters over consecutive steps — so some villagers couldn't eat; (2) warriors arrived in the Cave nearly hungry and had to turn back after <2 attacks. Fixes: bigger wheat reserve (2 meals per villager, plus don't spend on spawning unless a real buffer remains), villagers eat proactively at `steps_since_meal >= 4` (so they leave for the Cave well-fed), and Cave villagers only return at `>= 5` (they'll still make it home in time since they left freshly fed).

```py
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
        # 1) eat proactively: anyone at >= 4 steps hungry eats now,
        #    so warriors travel to the Cave freshly fed
        for c in components:
            if c.steps_since_meal >= 4:
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

        # 3) spawning — need a solid wheat buffer so nobody starves
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
            # they left the village freshly fed (<= 3 steps hungry on arrival),
            # so they can attack for several steps before heading home
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```