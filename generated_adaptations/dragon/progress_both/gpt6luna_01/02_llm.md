The strategy feeds villagers before they become unsafe, sends cave warriors back with enough time to eat, and otherwise keeps warriors attacking while farmers remain in the Village. It spawns one farmer and two warriors when there are two available villagers and enough wheat to pay the cost while keeping a small food reserve. Existing farmers are preferred as spawn-group members so warriors can reach the Cave sooner.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.last_spawn_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = set(group_ids)
        assignments = {}

        # Feed villagers with enough time to avoid reaching the starvation
        # threshold. Warriors eat earlier because they need a step to travel
        # back to the Cave after eating.
        for i, villager in enumerate(components):
            age = getattr(villager, "steps_since_meal", 0)
            role = getattr(villager, "role", "")
            if (role == "Warrior" and age >= 3) or (role != "Warrior" and age >= 4):
                assignments[i] = "eat"

        # Spawn at most one villager per step. Keep a small wheat reserve for
        # meals, and prefer farmers as spawn-group members so warriors can
        # continue toward the Cave.
        can_spawn_this_step = self.last_spawn_step != step
        target = None
        cost = 0
        if can_spawn_this_step:
            if self.spawned_farmers < 1:
                target, cost = "spawn farmer", 10
            elif self.spawned_warriors < 2:
                target, cost = "spawn warrior", 12

        if target is not None and environment.farm.wheat >= cost + 3:
            candidates = [i for i in range(len(components)) if i not in assignments]
            candidates.sort(
                key=lambda i: 0 if getattr(components[i], "role", "") == "Farmer" else 1
            )
            if len(candidates) >= 2:
                for i in candidates[:2]:
                    assignments[i] = target
                self.last_spawn_step = step
                if target == "spawn farmer":
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

            if group in groups:
                environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = set(group_ids)

        for villager in components:
            role = getattr(villager, "role", "")
            age = getattr(villager, "steps_since_meal", 0)

            if role != "Warrior":
                group = "village"
            elif age >= 3:
                # Return early enough to travel to the Village and eat before
                # starvation; the Village assignment will feed them on arrival.
                group = "village"
            else:
                group = "attack"

            if group in groups:
                environment.assign_group(villager, group)
```