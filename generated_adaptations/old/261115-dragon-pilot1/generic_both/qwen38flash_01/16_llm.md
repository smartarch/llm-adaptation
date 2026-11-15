

Looking at the 0% win rate again, I need a cleaner approach. The key insight I missed: warriors should enter the cave at `sms=0` to get the maximum 3-attack window (arrive at sms=1, attack at sms 1,2,3, must leave at sms=4). Warriors at `sms>=1` in village should eat first to reset to 0, then go out the next step. This produces a tight 6-step cycle: eat→travel→attack×3→travel (back→eat handled by forced eat at sms=5 arrival).

Also, I'll be much more aggressive on warrior spawning since we need ~4-6 warriors to maintain continuous attacks (since 3-attack / 7-step cycle needs ~3 staggered warriors minimum, plus buffer for deaths from dragon's 20%-chance devour per attack step).

```py
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
        # Want to enter cave at sms=0 to maximize attack window (3 attacks).
        # So: if sms == 0 -> go to cave now.
        #     if sms >= 1 -> eat to reset to 0, then go cave next step.
        #     (sms >= 5 is forced eat anyway; we handle proactively.)
        for w in warriors:
            if w.steps_since_meal == 0:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "eat")

        # === FARMERS ===
        # Eat when sms >= 4 to be safe (starving at 6).
        must_eat = [f for f in farmers if f.steps_since_meal >= 4]
        can_work = [f for f in farmers if f.steps_since_meal < 4]
        for f in must_eat:
            environment.assign_group(f, "eat")

        # === SPAWNING ===
        # Aggressively spawn warriors to build attack force.
        # Keep at least 1-2 farmers farming for wheat production.
        num_work = len(can_work)
        # Early: keep 1 farmer farming (high wheat need for spawns)
        # Mid/late: keep 2 (to feed growing population)
        min_farm = 2 if step > 10 else 1
        excess = max(0, num_work - min_farm)
        max_pairs = excess // 2

        # Spawn plan by phase
        if step <= 10:
            want_w = min(max_pairs, 2)
            want_f = min(max(0, max_pairs - want_w), 1)
        elif step <= 20:
            want_w = min(max_pairs, 1)
            want_f = min(max(0, max_pairs - want_w), 1)
        else:
            want_w = min(max_pairs, 1)
            want_f = 0

        # Affordability: prefer warriors (DPS) then farmers (food)
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
        # Attack while sms <= 3.
        # Must return at sms >= 4: arrive village at sms=5, eat (forced) next step.
        # Also return if HP is dangerously low to preserve warriors.
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            elif c.role == "Warrior" and c.hp <= 1:
                # Critically injured; don't risk being eaten/finished off
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```