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

        # --- Categorize by hunger ---
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        not_hungry = [c for c in components if c.steps_since_meal < 3]

        wheat_left = wheat

        # Feed hungry villagers (s_m >= 3)
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                environment.assign_group(c, "farm")

        rem_farmers = [c for c in not_hungry if c.role == "Farmer"]
        rem_warriors = [c for c in not_hungry if c.role == "Warrior"]

        # --- Estimate meals needed in next 1 step only ---
        meals_next = 0
        for c in not_hungry:
            if c.steps_since_meal >= 2:
                meals_next += 1
        for w in all_warriors:
            if w.location == "Village" and w.steps_since_meal >= 2:
                meals_next += 1
        for f in all_farmers:
            if f.location == "Village" and f.steps_since_meal >= 2:
                meals_next += 1
        # Anyone who was hungry but couldn't eat
        for c in hungry:
            if wheat <= 0:
                meals_next += 1

        reserve = meals_next
        spawn_budget = max(0, wheat_left - reserve)

        # --- AGGRESSIVE SPAWNING: target 10 warriors ---
        max_warriors = 10
        while total_warriors < max_warriors and spawn_budget >= 12:
            pool = rem_farmers + rem_warriors
            if len(pool) < 2:
                break
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            spawn_budget -= 12
            used = {id(pool[0]), id(pool[1])}
            rem_farmers = [c for c in rem_farmers if id(c) not in used]
            rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # --- SEND ALL non-hungry warriors to cave ---
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- ASSIGN FARMERS ---
        # Keep 2 farmers for wheat production (sustains ~12 villagers eating).
        # Surplus goes to cave for bonus damage (especially late game).
        min_farm = 2 if dragon_hp > 30 else 1
        for i, f in enumerate(rem_farmers):
            if i < min_farm:
                environment.assign_group(f, "farm")
            elif dragon_hp <= 70:
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST leave: travel takes 1 step → s_m=5 in village → eat next step.
                environment.assign_group(c, "village")
            else:
                # s_m in {0,1,2,3}: safe to attack
                environment.assign_group(c, "attack")