from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _find_group(self, group_ids, keyword):
        for g in group_ids:
            if keyword in g.lower():
                return g
        return None

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.wheat
        cave_group = self._find_group(group_ids, "cave")
        farm_group = self._find_group(group_ids, "farm")
        spawn_w_group = self._find_group(group_ids, "spawn warrior")

        if not cave_group:
            cave_group = group_ids[0]

        n = len(components)

        # Always send everything to cave UNLESS we can afford to keep 2 farming
        # Strategy: keep 2 farmers farming to produce wheat for warrior spawns
        # Spawn a warrior whenever wheat >= 12 and we have >= 4 components
        # (2 spawn + 2 farm)

        can_spawn = spawn_w_group and wheat >= 12 and n >= 4

        if can_spawn:
            # 2 farmers spawn warrior, rest go to cave to attack
            environment.assign_group(components[0], spawn_w_group)
            environment.assign_group(components[1], spawn_w_group)
            for i in range(2, n):
                environment.assign_group(components[i], cave_group)
        elif n >= 3 and step <= 1:
            # Early game: 1 farms, rest attack to chip the dragon
            if farm_group:
                environment.assign_group(components[0], farm_group)
                for i in range(1, n):
                    environment.assign_group(components[i], cave_group)
            else:
                for c in components:
                    environment.assign_group(c, cave_group)
        elif n >= 2 and farm_group:
            # Keep 1 farmer farming, send rest to cave
            environment.assign_group(components[0], farm_group)
            for i in range(1, n):
                environment.assign_group(components[i], cave_group)
        else:
            # Send everything to cave - we need damage NOW
            for c in components:
                environment.assign_group(c, cave_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        attack_group = self._find_group(group_ids, "attack")
        if not attack_group:
            attack_group = group_ids[0]

        for c in components:
            environment.assign_group(c, attack_group)