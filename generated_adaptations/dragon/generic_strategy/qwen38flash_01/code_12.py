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

        # Eat: warriors at sme>=3, farmers at sme>=5
        for c in eat_now:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Warriors ready for battle go to cave immediately
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # Aggressive spawning with farmers
        avail = list(farmers_pool)

        # Spawn warriors: 2 villagers + 12 wheat. As many as possible.
        while len(avail) >= 2 and rem_wheat >= 12:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers for sustained wheat income (only early game)
        if step <= 8:
            while len(avail) >= 2 and rem_wheat >= 10 and self.spawned_farmers < 2:
                c1 = avail.pop(0)
                c2 = avail.pop(0)
                environment.assign_group(c1, "spawn farmer")
                environment.assign_group(c2, "spawn farmer")
                rem_wheat -= 10
                self.spawned_farmers += 1

        # Remaining farmers farm
        for c in avail:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                sme = c.steps_since_meal
                if sme >= 6:
                    # Starving: 0 damage, losing HP. Must return to eat.
                    environment.assign_group(c, "village")
                else:
                    # sme 0-5: still deals full damage. ATTACK.
                    # At sme=5, attacking prevents +5 regen for 3 dmg.
                    # Next step sme=6 will force return with 1 HP loss.
                    environment.assign_group(c, "attack")
            else:
                # Non-warriors shouldn't be in cave; return to village
                environment.assign_group(c, "village")