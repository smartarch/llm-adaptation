from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        # Find the group that sends units to the cave
        cave_group = None
        for g in group_ids:
            if "cave" in g.lower():
                cave_group = g
                break

        if cave_group is None and group_ids:
            cave_group = group_ids[0]

        if cave_group is None:
            return

        # After step 3, send ALL components to cave.
        # First 3 steps: farm a bit to build wheat, send half to cave.
        if step <= 2 and len(components) >= 2:
            half = len(components) // 2
            for i, c in enumerate(components):
                if i < half:
                    # Try to find farm group
                    farm_group = None
                    for g in group_ids:
                        if "farm" in g.lower():
                            farm_group = g
                            break
                    if farm_group:
                        environment.assign_group(c, farm_group)
                    else:
                        environment.assign_group(c, cave_group)
                else:
                    environment.assign_group(c, cave_group)
        else:
            # Send EVERYTHING to cave to attack
            for c in components:
                environment.assign_group(c, cave_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # Find the attack group from the available groups
        attack_group = None
        for g in group_ids:
            if "attack" in g.lower():
                attack_group = g
                break

        if attack_group is None and group_ids:
            attack_group = group_ids[0]

        if attack_group is None:
            return

        # Assign EVERYTHING to attack. No exceptions.
        for c in components:
            environment.assign_group(c, attack_group)