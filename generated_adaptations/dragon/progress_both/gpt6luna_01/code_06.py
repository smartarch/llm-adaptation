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

        # Feed villagers in time to avoid starvation. Warriors returning from
        # the Cave are fed promptly so they can get back to attacking.
        for i, villager in enumerate(components):
            age = getattr(villager, "steps_since_meal", 0)
            role = getattr(villager, "role", "")
            if (role == "Warrior" and age >= 4) or (role != "Warrior" and age >= 5):
                assignments[i] = "eat"

        # Secure the required extra farmer, then continue producing warriors.
        # Farmers can provide spawn-group members while warriors travel or fight.
        if self.spawned_farmers < 1:
            spawn_group, cost = "spawn farmer", 10
        else:
            spawn_group, cost = "spawn warrior", 12

        wheat = getattr(environment.farm, "wheat", 0)
        if (
            self.last_spawn_step != step
            and wheat >= cost + 3
        ):
            candidates = [i for i in range(len(components)) if i not in assignments]
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
        dragon_hp = getattr(environment.dragon, "hp", 100)

        warriors = [v for v in components if getattr(v, "role", "") == "Warrior"]
        # If the present cave force can plausibly finish the Dragon, keep it
        # attacking rather than interrupting the final assault for meals.
        commit_to_finish = dragon_hp <= 3 * len(warriors)

        for villager in components:
            role = getattr(villager, "role", "")
            age = getattr(villager, "steps_since_meal", 0)

            if role != "Warrior":
                group = "village"
            elif age >= 4 and not commit_to_finish:
                group = "village"
            else:
                group = "attack"

            if group in valid_groups:
                environment.assign_group(villager, group)