from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # ---- WARRIORS ----
        # Enter cave at sms=0 to maximize attack window (attacks at sms 0,1,2,3).
        # Otherwise eat to reset sms to 0, then go cave next step.
        for w in warriors:
            if w.steps_since_meal == 0 and w.hp > 1:
                environment.assign_group(w, "cave")
            else:
                # sms >= 1 -> eat; also low-hp warriors stay & eat to recover (no, hp doesn't regen,
                # but we still must avoid them dying in cave). Eat then go out again; they will
                # likely die on their next cave trip but that's unavoidable.
                environment.assign_group(w, "eat")

        # ---- FARMERS ----
        must_eat = [f for f in farmers if f.steps_since_meal >= 4]
        can_work = [f for f in farmers if f.steps_since_meal < 4]
        for f in must_eat:
            environment.assign_group(f, "eat")

        # ---- SPAWNING ----
        # Strategy: we need many warriors. Spawning a warrior needs 2 villagers + 12 wheat.
        # Spawning a farmer needs 2 villagers + 10 wheat (only useful as a spawn "engine"
        # and food source). We should NEVER use a warrior as a spawn-pair member unless
        # we have spare warriors.
        num_farm = len(can_work)
        num_war = len(warriors)

        # We want at least 1 farmer left farming for wheat; the rest of the farmers go to
        # spawning. Use pairs of farmers for spawning.
        min_farming = 1
        farmer_pairs_for_spawn = max(0, num_farm - min_farming) // 2

        # Decide spawn targets. Always prefer warrior spawns (DPS). If we have very few
        # farmers (1) we cannot spawn warrior without using a warrior as pair; do that
        # only when wheat is plentiful and we have >=2 warriors already.
        actual_warrior = 0
        actual_farmer = 0
        wb = wheat

        # Phase-based plan
        if step <= 8:
            target_w = farmer_pairs_for_spawn
            target_f = 0
        elif step <= 18:
            target_w = min(farmer_pairs_for_spawn, 1)
            target_f = min(max(0, farmer_pairs_for_spawn - target_w), 1)
        else:
            target_w = min(farmer_pairs_for_spawn, 1)
            target_f = 0

        # Affordability
        for _ in range(target_w):
            if wb >= 12:
                actual_warrior += 1
                wb -= 12
        for _ in range(target_f):
            if wb >= 10:
                actual_farmer += 1
                wb -= 10

        # If we still have farmer-pairs but can't afford warrior (not enough wheat),
        # maybe spawn farmers? No - farmers don't kill dragon. Skip.

        sw = actual_warrior * 2
        sf = actual_farmer * 2
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
        # Attack while sms <= 3 (so we get 4 attacks: at sms 0,1,2,3).
        # Must leave at sms >= 4: arrive village at sms=5, eat next step (no starvation).
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            elif c.role == "Warrior" and c.hp <= 1:
                # too fragile; preserve
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")