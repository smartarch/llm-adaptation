import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        total_warriors = len(all_warriors)
        total_villagers = total_warriors + len(all_farmers)

        # --- Categorize by hunger ---
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        not_hungry = [c for c in components if c.steps_since_meal < 3]

        wheat_left = wheat

        # Feed hungry villagers (s_m >= 3): eat NOW to avoid starvation
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat available: must farm
                environment.assign_group(c, "farm")

        # Separate remaining (s_m < 3) by role
        rem_farmers = [c for c in not_hungry if c.role == "Farmer"]
        rem_warriors = [c for c in not_hungry if c.role == "Warrior"]

        # --- Estimate wheat reserve for upcoming meals ---
        meals_urgent = 0
        for w in all_warriors:
            if w.location == "Village" and w.steps_since_meal >= 2:
                meals_urgent += 1
        for f in all_farmers:
            if f.location == "Village" and f.steps_since_meal >= 2:
                meals_urgent += 1
        for c in not_hungry:
            if c.steps_since_meal >= 1:
                meals_urgent += 1
        reserve = max(meals_urgent, 2)
        spawn_budget = max(0, wheat_left - reserve)

        # --- AGGRESSIVE SPAWNING ---
        spawned = 0
        while total_warriors + spawned < 8 and spawn_budget >= 12:
            pool = rem_farmers + rem_warriors
            if len(pool) < 2:
                break
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            spawn_budget -= 12
            spawned += 1
            used = {id(pool[0]), id(pool[1])}
            rem_farmers = [c for c in rem_farmers if id(c) not in used]
            rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # --- SEND ALL non-hungry warriors to CAVE immediately ---
        # Warriors at s_m=0 or s_m=1 can get 3 or 2 attacks in cave!
        # Even at s_m=2 they get 1-2 attacks which is still valuable.
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- ASSIGN FARMERS ---
        # Need enough farmers to produce wheat for meals
        # Each farmer produces 5 wheat. Need ~total/6 wheat per step for meals.
        min_farm = 1 if dragon_hp <= 25 else 2
        for i, f in enumerate(rem_farmers):
            if i < min_farm:
                environment.assign_group(f, "farm")
            elif dragon_hp <= 20:
                # Endgame: send surplus farmers to cave for extra damage
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST go to village NOW.
                # Travel takes 1 step: s_m becomes 5. Then eat next step. Safe.
                # If they attack: s_m becomes 5, then travel → s_m=6 = starving!
                environment.assign_group(c, "village")
            else:
                # s_m in {0,1,2,3}: safe to attack
                # After attack, s_m increments. At s_m=4 next step, they leave.
                # At s_m=3: attack → s_m=4 → travel → s_m=5 → eat → safe.
                environment.assign_group(c, "attack")