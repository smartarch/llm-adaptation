import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        remaining_wheat = wheat

        # Categorize villagers
        critical_eat = []      # sme >= 5 (any role) - about to starve
        warriors_eat = []      # warriors at sme == 4 - should eat before going to cave
        warriors_go = []       # warriors at sme < 4 - ready to attack
        farmers_ready = []     # farmers at sme < 5 - available for tasks

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    critical_eat.append(c)
                elif c.steps_since_meal >= 4:
                    warriors_eat.append(c)
                else:
                    warriors_go.append(c)
            else:  # Farmer
                if c.steps_since_meal >= 5:
                    critical_eat.append(c)
                else:
                    farmers_ready.append(c)

        # Priority 1: Critical eaters (sme >= 5) - must eat or starve
        for c in critical_eat:
            if remaining_wheat >= 1:
                environment.assign_group(c, "eat")
                remaining_wheat -= 1
            else:
                # No wheat to eat; assign to farm (they'll take starvation damage)
                environment.assign_group(c, "farm")

        # Priority 2: Warriors at sme==4 should eat before traveling to cave
        for c in warriors_eat:
            if remaining_wheat >= 1:
                environment.assign_group(c, "eat")
                remaining_wheat -= 1
            else:
                # No wheat; send to cave (they'll starve but at least deal damage for now)
                environment.assign_group(c, "cave")

        # Priority 3: Warriors ready to go attack
        for c in warriors_go:
            environment.assign_group(c, "cave")

        # Priority 4: Spawning and farming for farmers
        available = list(farmers_ready)

        # Spawn warriors first (need 2 villagers, 12 wheat), up to 3
        while len(available) >= 2 and remaining_wheat >= 12 and self.spawned_warriors < 3:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            remaining_wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers (need 2 villagers, 10 wheat), up to 2
        while len(available) >= 2 and remaining_wheat >= 10 and self.spawned_farmers < 2:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            remaining_wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers farm
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        for c in warriors:
            if c.steps_since_meal >= 5:
                # Critical: must leave immediately (will arrive hungry but can eat next step)
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= 4:
                # Should return to village to eat (arrives at sme=5, eats next step)
                environment.assign_group(c, "village")
            else:
                # Ready to attack
                environment.assign_group(c, "attack")

        # Non-warriors in cave shouldn't be here; send back to village
        for c in others:
            environment.assign_group(c, "village")