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
                # Eat as soon as back so the cycle stays tight; otherwise head to cave.
                if sme >= 2:
                    eat_now.append(c)
                else:
                    warriors_to_cave.append(c)
            else:
                if sme >= 4:
                    eat_now.append(c)
                else:
                    farmers_pool.append(c)

        # Feed returning warriors / hungry farmers.
        for c in eat_now:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Fresh warriors immediately reinforce the cave.
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # Build an aggressive spearhead: spawn warriors whenever affordable.
        avail = list(farmers_pool)
        while len(avail) >= 2 and rem_wheat >= 12 and self.spawned_warriors < 5:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Add wheat producers to sustain the warrior horde (early game only).
        while len(avail) >= 2 and rem_wheat >= 10 and step <= 6 and self.spawned_farmers < 3:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            rem_wheat -= 10
            self.spawned_farmers += 1

        # Everyone else farms to keep wheat flowing.
        for c in avail:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                sme = c.steps_since_meal
                if sme >= 6:
                    # Starving (0 dmg, losing HP): head home to eat.
                    environment.assign_group(c, "village")
                else:
                    # sme 0-5 deals full 3 dmg; attacking also cancels regen.
                    environment.assign_group(c, "attack")
            else:
                # Farmers don't belong in the cave; send them home to farm/eat.
                environment.assign_group(c, "village")