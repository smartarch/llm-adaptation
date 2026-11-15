

Looking at the 33% win rate with 19-step average, the main issues are:
1. **Not enough warriors** attacking simultaneously (dragon regens 5/step, need 2+ warriors constantly)
2. **Staggering** isn't working well - gaps in attack coverage cause massive regen
3. **Spawning too conservative** - need warriors ASAP
4. **Cave logic** sends warriors back too early, creating coverage gaps

Key strategy changes:
- **No spawn limits** - spawn warriors as aggressively as wheat allows
- **Simpler cave logic**: warriors attack unless sme≥5 (must return to eat)
- **Village logic**: warriors go to cave if sme<3, eat if sme≥3 (eat while sme=3 means at cave sme=4, can attack 4 steps safely)
- **Farmers**: just farm and spawn, minimal cave involvement
- **Stagger naturally** by sending warriors to cave at different sme values

```py
import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        rem_wheat = wheat

        # Sort components: critical eaters first, then warriors, then farmers
        must_eat = []
        warriors_eat = []
        warriors_go = []
        farmers = []

        for c in components:
            sme = c.steps_since_meal
            if sme >= 5:
                must_eat.append(c)
            elif c.role == "Warrior":
                if sme >= 3:
                    warriors_eat.append(c)
                else:
                    warriors_go.append(c)
            else:
                farmers.append(c)

        # Critical eaters (sme>=5) MUST eat
        for c in must_eat:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                # No wheat: they'll starve but at least try to farm for wheat
                environment.assign_group(c, "farm")

        # Warriors at sme 3-4: eat now so they can survive 4-5 attacks in cave
        for c in warriors_eat:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Warriors at sme < 3: send to cave to attack
        for c in warriors_go:
            environment.assign_group(c, "cave")

        # Use farmers to spawn warriors aggressively, then farmers, then farm
        available = list(farmers)

        # Spawn warriors: need 2 villagers + 12 wheat. Be very aggressive.
        while len(available) >= 2 and rem_wheat >= 12 and self.spawned_warriors < 6:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers for wheat production (need 2 villagers + 10 wheat)
        while len(available) >= 2 and rem_wheat >= 10 and self.spawned_farmers < 3:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            rem_wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers farm
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        # Count warriors that will still be able to attack next step
        # A warrior with sme X attacks this step, will have sme X+1 next step
        # They can attack next step if sme+1 < 5, i.e. sme < 4, i.e. sme <= 3
        will_cover_next = sum(1 for w in warriors if w.steps_since_meal <= 3)

        for c in warriors:
            sme = c.steps_since_meal
            if sme >= 5:
                # Must return now: at sme=5 we could attack one more time,
                # but then sme=6 next step means 0 damage + HP loss in cave.
                # Better to travel now (sme=6 travel = 1 HP loss but arrive village).
                environment.assign_group(c, "village")
            elif sme == 4:
                # Attack this step (sme becomes 5). Next step either attack at sme=5
                # or return. Only return now if coverage is good.
                if will_cover_next >= 2:
                    # Plenty of coverage, go eat to prepare for next cycle
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                # sme 0-3: always attack
                environment.assign_group(c, "attack")

        # Non-warriors in cave: return to village
        for c in others:
            environment.assign_group(c, "village")
```