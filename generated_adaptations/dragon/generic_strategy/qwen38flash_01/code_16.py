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

        # Feed those who need it (warriors eat at sme>=3, farmers at sme>=5)
        for c in eat_now:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                # Fallback: farm for wheat, will take starvation damage
                environment.assign_group(c, "farm")

        # Fresh warriors head straight to the cave
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # Aggressive warrior spawning - no artificial cap beyond supply
        avail = list(farmers_pool)
        while len(avail) >= 2 and rem_wheat >= 12:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Spawn a couple of farmers early for sustainable wheat income
        while len(avail) >= 2 and rem_wheat >= 10 and step <= 8 and self.spawned_farmers < 2:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            rem_wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers produce wheat
        for c in avail:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                sme = c.steps_since_meal
                if sme >= 6:
                    # Starving: deals 0 dmg and loses HP each step. Must leave.
                    environment.assign_group(c, "village")
                else:
                    # sme 0-5 all deal full 3 damage AND cancel dragon regen.
                    environment.assign_group(c, "attack")
            else:
                # Non-warriors don't belong in cave; send home.
                environment.assign_group(c, "village")