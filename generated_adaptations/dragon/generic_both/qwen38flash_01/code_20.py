from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # === WARRIORS ===
        # Requirement: warriors with sms >= 3 must NOT go to cave (must eat first).
        # Warriors with sms <= 2 can go to cave; they'll attack as long as sms allows.
        # Natural staggering arises because warriors arrive in village at different sms values.
        for w in warriors:
            if w.steps_since_meal >= 3:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # === FARMERS: must eat before starving ===
        # Eat at sms >= 4 to be safe (starvation begins after 6 consecutive non-eating steps).
        must_eat = [f for f in farmers if f.steps_since_meal >= 4]
        can_work = [f for f in farmers if f.steps_since_meal < 4]
        for f in must_eat:
            environment.assign_group(f, "eat")

        # === FARMERS: farm or spawn ===
        # Aggressively spawn warriors to build a continuous attack force.
        # Each warrior spawn consumes 12 wheat and 2 villagers (we use farmer pairs).
        # Keep at least 1 farmer farming for wheat; everything else tries to spawn warriors.
        num_work = len(can_work)
        min_farming = 1
        excess = max(0, num_work - min_farming)
        pairs = excess // 2

        # Early game: dump everything into warrior spawning.
        # Mid game: still mostly warriors, occasionally a farmer for food.
        # Late game (step >= 24): stop spawning, maximize farming for food.
        if step <= 16:
            want_w = pairs
            want_f = 0
        elif step <= 23:
            want_w = min(pairs, 1)
            want_f = min(max(0, pairs - want_w), 1)
        else:
            want_w = 0
            want_f = 0

        # Affordability: warriors first (DPS is the bottleneck), then farmers.
        actual_w = 0
        actual_f = 0
        wb = wheat
        for _ in range(want_w):
            if wb >= 12:
                actual_w += 1
                wb -= 12
        for _ in range(want_f):
            if wb >= 10:
                actual_f += 1
                wb -= 10

        sw = actual_w * 2
        sf = actual_f * 2
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
        # Attack as long as it's safe (sms <= 3). At sms >= 4, the warrior must
        # return to village: they'll arrive at sms=5 and eat the next step,
        # avoiding starvation at sms=6.
        # Also preserve very-low-HP warriors by sending them back.
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            elif c.role == "Warrior" and c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")