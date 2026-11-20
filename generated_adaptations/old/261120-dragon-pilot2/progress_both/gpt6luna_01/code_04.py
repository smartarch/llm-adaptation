from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.last_spawn_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)
        assignments = {}

        # Feed villagers before they reach the starvation threshold.
        # A returning warrior may arrive with age 5, so eat immediately.
        for i, villager in enumerate(components):
            age = getattr(villager, "steps_since_meal", 0)
            role = getattr(villager, "role", "")
            if (role == "Warrior" and age >= 4) or (role != "Warrior" and age >= 5):
                assignments[i] = "eat"

        # First ensure at least one farmer is spawned, then build a large
        # warrior force. The reserve helps cover meals and avoids spending
        # the last wheat on spawning.
        if self.spawned_farmers < 1:
            spawn_group, cost = "spawn farmer", 10
        elif self.spawned_warriors < 6:
            spawn_group, cost = "spawn warrior", 12
        else:
            spawn_group, cost = None, 0

        if (
            spawn_group is not None
            and self.last_spawn_step != step
            and getattr(environment.farm, "wheat", 0) >= cost + 5
        ):
            candidates = [i for i in range(len(components)) if i not in assignments]
            # Use farmers as spawn-group members where possible, allowing
            # warriors to head to the Cave promptly.
            candidates.sort(
                key=lambda i: 0 if getattr(components[i], "role", "") == "Farmer" else 1
            )
            if len(candidates) >= 2:
                for i in candidates[:2]:
                    assignments[i] = spawn_group
                self.last_spawn_step = step
                if spawn_group == "spawn farmer":
                    self.spawned_farmers += 1
                else:
                    self.spawned_warriors += 1

        for i, villager in enumerate(components):
            if i in assignments:
                group = assignments[i]
            elif getattr(villager, "role", "") == "Warrior":
                group = "cave"
            else:
                group = "farm"

            if group in valid_groups:
                environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        valid_groups = set(group_ids)

        for villager in components:
            role = getattr(villager, "role", "")
            age = getattr(villager, "steps_since_meal", 0)

            if role != "Warrior":
                group = "village"
            elif age >= 4:
                # One step to return, then the Village assignment feeds
                # warriors at age 4 or later before they leave again.
                group = "village"
            else:
                group = "attack"

            if group in valid_groups:
                environment.assign_group(villager, group)