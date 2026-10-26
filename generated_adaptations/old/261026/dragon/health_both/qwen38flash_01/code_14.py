from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        # Find actual group names from the environment's group_ids
        cave_group = None
        farm_group = None
        for g in group_ids:
            gl = g.lower()
            if "cave" in gl:
                cave_group = g
            elif "farm" in gl:
                farm_group = g

        if cave_group is None:
            cave_group = group_ids[0] if group_ids else "cave"

        n = len(components)

        # Strategy that worked before: keep a small farm buffer early,
        # then send EVERYTHING to cave to attack.
        if step <= 1 and n >= 2 and farm_group:
            half = max(1, n // 2)
            for i in range(half):
                environment.assign_group(components[i], farm_group)
            for i in range(half, n):
                environment.assign_group(components[i], cave_group)
        else:
            # Send everything to the cave to attack the dragon
            for c in components:
                environment.assign_group(c, cave_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # Find actual attack group name
        attack_group = None
        for g in group_ids:
            if "attack" in g.lower():
                attack_group = g
                break

        if attack_group is None:
            attack_group = group_ids[0] if group_ids else "attack"

        # Everyone in the cave attacks unconditionally
        for c in components:
            environment.assign_group(c, attack_group)