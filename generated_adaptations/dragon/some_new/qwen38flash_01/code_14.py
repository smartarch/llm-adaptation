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
        ok = [c for c in components if c.steps_since_meal < 3]

        wheat_left = wheat

        # Feed hungry villagers (s_m >= 3)
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat available, must farm
                environment.assign_group(c, "farm")

        # Remaining non-hungry villagers
        rem_farmers = [c for c in ok if c.role == "Farmer"]
        rem_warriors = [c for c in ok if c.role == "Warrior"]

        # --- Estimate meals needed in next 1 step ---
        # Only count villagers who will be s_m >= 3 next step
        meals_next_step = 0
        for w in all_warriors:
            if w.location == "Village" and w.steps_since_meal >= 2:
                meals_next_step += 1
        for f in all_farmers:
            if f.location == "Village" and f.steps_since_meal >= 2:
                meals_next_step += 1
        # Also villagers who couldn't eat because no wheat
        for c in hungry:
            if wheat <= 0:
                meals_next_step += 1

        reserve = max(meals_next_step, 1)
        spawn_budget = wheat_left - reserve

        # --- AGGRESSIVE SPAWNING ---
        # Spawn warriors as much as possible, up to 8 total
        if total_warriors < 8 and spawn_budget >= 12:
            # Pick 2 villagers to form spawn pair
            if len(rem_farmers) >= 2:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_farmers[1], "spawn warrior")
                spawn_budget -= 12
                used = {id(rem_farmers[0]), id(rem_farmers[1])}
                rem_farmers = [c for c in rem_farmers if id(c) not in used]
            elif len(rem_farmers) >= 1 and len(rem_warriors) >= 1:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_warriors[0], "spawn warrior")
                spawn_budget -= 12
                rem_farmers = rem_farmers[1:]
                rem_warriors = rem_warriors[1:]
            elif len(rem_warriors) >= 2:
                environment.assign_group(rem_warriors[0], "spawn warrior")
                environment.assign_group(rem_warriors[1], "spawn warrior")
                spawn_budget -= 12
                used = {id(rem_warriors[0]), id(rem_warriors[1])}
                rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # Second spawn attempt if budget allows
        if total_warriors < 8 and spawn_budget >= 12:
            if len(rem_farmers) >= 2:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_farmers[1], "spawn warrior")
                spawn_budget -= 12
                used = {id(rem_farmers[0]), id(rem_farmers[1])}
                rem_farmers = [c for c in rem_farmers if id(c) not in used]
            elif len(rem_farmers) >= 1 and len(rem_warriors) >= 1:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_warriors[0], "spawn warrior")
                spawn_budget -= 12
                rem_farmers = rem_farmers[1:]
                rem_warriors = rem_warriors[1:]
            elif len(rem_warriors) >= 2:
                environment.assign_group(rem_warriors[0], "spawn warrior")
                environment.assign_group(rem_warriors[1], "spawn warrior")
                spawn_budget -= 12
                used = {id(rem_warriors[0]), id(rem_warriors[1])}
                rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # --- ALL remaining warriors go to cave ---
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- Assign farmers ---
        # Keep 1-2 farmers farming for wheat. Surplus goes to cave.
        min_farm = min(2, len(rem_farmers))
        for i, f in enumerate(rem_farmers):
            if i < min_farm:
                environment.assign_group(f, "farm")
            elif dragon_hp <= 60:
                # Mid/late game: send surplus farmers to cave for extra damage
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST go to village: travel(1)→s_m=5, then eat→s_m=0
                environment.assign_group(c, "village")
            else:
                # s_m in {0,1,2,3}: safe to attack
                environment.assign_group(c, "attack")