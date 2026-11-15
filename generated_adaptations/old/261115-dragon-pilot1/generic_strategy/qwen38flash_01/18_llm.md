

To beat 20.7 steps we must reach a high *concurrent* attacker count earlier, because net damage/step ≈ 3·(#warriors attacking every step) − 5·(#unattacked steps). The current cycle already removes most regen gaps; the remaining lever is the **ramp‑up phase**, which is limited by wheat income. With only the starting farmer (5 wheat/step) it's slow to afford the 12‑wheat warrior spawns.

Improvement: build a stronger wheat engine early by spawning **3 farmers** (instead of 2) within a slightly wider early window, so that mid‑game we have surplus wheat to feed an unlimited, faster‑growing warrior horde. All other tuned mechanics that produced the 100% win are kept identical (warriors attack through sme=5 and only leave at sme≥6; warriors eat at sme≥3; warriors always reinforce the cave at sme<3; unlimited warrior spawns).

```py
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
                environment.assign_group(c, "farm")

        # Fresh warriors head straight to the cave to sustain attack coverage
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        avail = list(farmers_pool)

        # Aggressive warrior spawning - as many as wheat + villagers allow
        while len(avail) >= 2 and rem_wheat >= 12:
            c1 = avail.pop(0)
            c2 = avail.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Build a stronger wheat engine early so warrior spawning stays unblocked
        while len(avail) >= 2 and rem_wheat >= 10 and step <= 10 and self.spawned_farmers < 3:
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
                    # sme 0-5 deal full 3 damage AND cancel dragon regen.
                    environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```