import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        rem_wheat = environment.farm.wheat

        eat_now = []
        warriors_to_cave = []
        farmers_pool = []

        for c in components:
            sme = c.steps_since_meal
            if c.role == "Warrior":
                if sme >= 3:
                    eat_now.append(c)
                else:
                    warriors_to_cave.append(c)
            else:
                if sme >= 5:
                    eat_now.append(c)
                else:
                    farmers_pool.append(c)

        # Feed warriors (eat at sme>=3 so they can take a full 5-attack cave trip)
        # and starving farmers (sme>=5).
        for c in eat_now:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Fresh warriors immediately go to the cave to keep attack coverage dense.
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        avail = list(farmers_pool)

        # Aggressive, uncapped warrior spawning whenever villagers + wheat allow.
        while len(avail) >= 2 and rem_wheat >= 12:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Build a small wheat engine early so warrior spawning never stalls.
        while len(avail) >= 2 and rem_wheat >= 10 and step <= 8 and self.spawned_farmers < 2:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            rem_wheat -= 10
            self.spawned_farmers += 1

        # Everyone else farms to keep wheat flowing for spawns.
        for c in avail:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                sme = c.steps_since_meal
                if sme >= 6:
                    # Starving: deals 0 damage and loses HP each step -> must leave.
                    environment.assign_group(c, "village")
                else:
                    # sme 0-5 deal full 3 damage and cancel the dragon's +5 regen.
                    environment.assign_group(c, "attack")
            else:
                # Non-warriors don't belong in the cave.
                environment.assign_group(c, "village")