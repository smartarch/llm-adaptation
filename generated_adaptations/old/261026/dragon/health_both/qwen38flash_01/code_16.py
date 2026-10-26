from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.wheat
        n = len(components)

        # Identify valid groups from the environment
        cave_group = None
        farm_group = None
        spawn_w_group = None
        for g in group_ids:
            if g == "cave":
                cave_group = g
            elif g == "farm":
                farm_group = g
            elif g == "spawn warrior":
                spawn_w_group = g

        if cave_group is None:
            cave_group = group_ids[0] if group_ids else "cave"

        # Try to spawn a warrior if we have plenty of bodies and wheat
        if (
            spawn_w_group is not None
            and wheat >= 12
            and n >= 5
        ):
            environment.assign_group(components[0], spawn_w_group)
            environment.assign_group(components[1], spawn_w_group)
            for i in range(2, n):
                if farm_group and i < n - 2:
                    environment.assign_group(components[i], cave_group)
                else:
                    environment.assign_group(components[i], cave_group)
            return

        # Proven working strategy from 33% run
        if step <= 1 and n >= 2 and farm_group:
            half = max(1, n // 2)
            for i in range(half):
                environment.assign_group(components[i], farm_group)
            for i in range(half, n):
                environment.assign_group(components[i], cave_group)
        else:
            for c in components:
                environment.assign_group(c, cave_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        attack_group = None
        for g in group_ids:
            if g == "attack":
                attack_group = g
                break

        if attack_group is None:
            attack_group = group_ids[0] if group_ids else "attack"

        for c in components:
            environment.assign_group(c, attack_group)