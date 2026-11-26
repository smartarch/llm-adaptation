from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        gid = set(group_ids)  # group_ids are the names to pass to assign_group
        wheat = environment.farm.wheat

        all_warriors = environment.warriors
        all_farmers = environment.farmers
        n_total = len(all_warriors) + len(all_farmers)
        n_warriors_total = len(all_warriors)

        assigned = set()
        # 1) starving villagers eat
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(c)

        remaining = [c for c in components if c not in assigned]

        # 2) warriors go to the cave to attack
        for c in remaining:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                assigned.add(c)
        remaining = [c for c in remaining if c not in assigned]

        # 3) spawning decisions for farmers
        # reserve: 1 meal per villager per step buffer
        reserve = n_total
        affordable_w = wheat - 12 >= reserve
        affordable_f = wheat - 10 >= reserve

        spawn_w = False
        spawn_f = False
        if affordable_w:
            if n_warriors_total == 0:
                spawn_w = True  # urgently need warriors
            elif n_total < 5:
                spawn_w = True
        if affordable_f and n_total < 5 and not spawn_w:
            spawn_f = True

        n_spawn_w = 2 if spawn_w else 0
        n_spawn_f = 2 if spawn_f else 0

        # keep at least 1 farmer farming if possible
        if len(remaining) - n_spawn_w - n_spawn_f < 1:
            n_spawn_f = max(0, len(remaining) - n_spawn_w - 1)

        for i, c in enumerate(remaining):
            if i < n_spawn_w:
                environment.assign_group(c, "spawn warrior")
            elif i < n_spawn_w + n_spawn_f:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # travel back takes a step; leave early enough to eat in time
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")