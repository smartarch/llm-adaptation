from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warrior rule: eat if sms>=2 (reset to 0, then next step go cave for full 3-attack cycle)
        # Go to cave if sms<=1 (arrive at sms 2 or 1, still get 1-3 attacks)
        # sms>=3 must eat per game requirement
        for w in warriors:
            if w.steps_since_meal >= 2:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # Farmer eat logic
        must_eat = [f for f in farmers if f.steps_since_meal >= 4]
        can_work = [f for f in farmers if f.steps_since_meal < 4]

        for f in must_eat:
            environment.assign_group(f, "eat")

        # Spawning: use pairs of farmers to create warriors first, then farmers
        num_work = len(can_work)
        min_farm = 2

        excess = max(0, num_work - min_farm)
        max_pairs = excess // 2

        # Spawn targets by phase
        if step <= 8:
            tw = min(max_pairs, 2)
            tf = min(max(0, max_pairs - tw), 1)
        elif step <= 18:
            tw = min(max_pairs, 1)
            tf = min(max(0, max_pairs - tw), 1)
        else:
            tw = 0
            tf = 0

        # Wheat check: prefer warriors (3dmg) over farmers (food)
        aw = 0
        af = 0
        wb = wheat
        for _ in range(tw):
            if wb >= 12:
                aw += 1
                wb -= 12
        for _ in range(tf):
            if wb >= 10:
                af += 1
                wb -= 10

        sw = aw * 2
        sf = af * 2
        idx = 0
        for f in can_work:
            if idx < sw:
                environment.assign_group(f, "spawn warrior")
            elif idx < sw + sf:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        # Attack while sms <= 3 (arrive at 1-3, attack until 4)
        # Return at sms >= 4 (arrive village at 5, eat next step)
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")