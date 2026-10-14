from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.wheat
        n = len(components)

        if n == 0:
            return

        # Be extremely aggressive: almost everyone goes to cave to attack.
        # Only keep a couple farmers to farm if we have plenty and wheat is low.
        # But never delay attacks past step 2.

        should_farm = (
            step <= 1
            and wheat < 6
            and n >= 3
        )

        if should_farm:
            # Keep up to 2 for farming, rest go to cave
            farm_count = min(2, n - 1)
            for i in range(farm_count):
                environment.assign_group(components[i], "farm")
            for i in range(farm_count, n):
                environment.assign_group(components[i], "cave")
        elif wheat >= 12 and n >= 4:
            # Occasionally spawn using 2 farmers (try every few turns)
            if step % 4 == 0:
                environment.assign_group(components[0], "spawn warrior")
                environment.assign_group(components[1], "spawn warrior")
                for i in range(2, n):
                    environment.assign_group(components[i], "cave")
            else:
                # Everyone goes to cave
                for c in components:
                    environment.assign_group(c, "cave")
        else:
            # SEND EVERYTHING TO CAVE - attack now!
            for c in components:
                environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        # NO role checking - assign EVERYONE in cave to attack
        # This handles cases where role string may differ from expected
        for c in components:
            environment.assign_group(c, "attack")