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

        # --- Categorize by hunger (feed at s_m >= 3) ---
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        not_hungry = [c for c in components if c.steps_since_meal < 3]

        wheat_left = wheat

        # Feed hungry villagers first (mandatory)
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat: must farm to recover, will eat next step
                environment.assign_group(c, "farm")

        rem_farmers = [c for c in not_hungry if c.role == "Farmer"]
        rem_warriors = [c for c in not_hungry if c.role == "Warrior"]

        # --- Wheat reserve for upcoming meals (next 2 steps) ---
        meals_upcoming = 0
        for w in all_warriors:
            if w.steps_since_meal >= 2:
                meals_upcoming += 1
        for f in all_farmers:
            if f.steps_since_meal >= 2:
                meals_upcoming += 1
        # Villagers in village not yet fed this step with s_m >= 1
        for c in not_hungry:
            if c.steps_since_meal >= 1:
                meals_upcoming += 1
        # Villagers who couldn't eat due to no wheat
        for c in hungry:
            if wheat <= 0:
                meals_upcoming += 1

        reserve = meals_upcoming
        spawn_wheat = max(0, wheat_left - reserve)

        # --- AGGRESSIVE SPAWNING (target 10 warriors) ---
        max_warriors = 10
        spawned = 0
        while (total_warriors + spawned) < max_warriors and spawn_wheat >= 12:
            pool = rem_farmers + rem_warriors
            if len(pool) < 2:
                break
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            spawn_wheat -= 12
            spawned += 1
            used = {id(pool[0]), id(pool[1])}
            rem_farmers = [c for c in rem_farmers if id(c) not in used]
            rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # --- Send ALL remaining warriors to cave immediately ---
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- Keep 2 farmers farming; never send farmers to cave ---
        num_farmers = len(rem_farmers)
        min_farm = min(2, num_farmers)
        for i, f in enumerate(rem_farmers):
            if i < min_farm:
                environment.assign_group(f, "farm")
            else:
                # Extra farmers also farm to build wheat surplus for more spawns
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST go to village: travel 1 step → s_m=5 → eat next step
                # If they attack at s_m=4, next step s_m=5, travel → s_m=6 = starve
                environment.assign_group(c, "village")
            else:
                # s_m 0-3: safe to attack
                environment.assign_group(c, "attack")