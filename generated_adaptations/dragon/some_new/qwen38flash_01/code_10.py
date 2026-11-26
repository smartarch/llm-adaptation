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
        total_villagers = len(all_warriors) + len(all_farmers)
        total_warriors = len(all_warriors)
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")

        # --- Categorize by hunger ---
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        not_hungry = [c for c in components if c.steps_since_meal < 3]

        # --- Feed hungry villagers first ---
        wheat_left = wheat
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat - must farm to produce food
                environment.assign_group(c, "farm")

        # --- Separate remaining by role ---
        rem_farmers = [c for c in not_hungry if c.role == "Farmer"]
        rem_warriors = [c for c in not_hungry if c.role == "Warrior"]

        # --- Estimate wheat needed for upcoming meals ---
        # Villagers in cave who will need to eat in next 1-2 steps
        upcoming_eaters = 0
        for w in all_warriors:
            if w.location == "Cave" and w.steps_since_meal >= 2:
                upcoming_eaters += 1
        for f in all_farmers:
            if f.location == "Cave" and f.steps_since_meal >= 2:
                upcoming_eaters += 1
        # Villagers in village approaching meal
        for c in not_hungry:
            if c.steps_since_meal >= 1:
                upcoming_eaters += 1

        wheat_reserve = max(upcoming_eaters, total_villagers // 5)
        spawn_wheat = wheat_left - wheat_reserve

        # --- SPAWNING: aggressive ---
        # Critical: zero warriors means dragon is safe - spawn NOW
        if total_warriors == 0 and spawn_wheat >= 12 and len(rem_farmers) + len(rem_warriors) >= 2:
            pool = rem_farmers if len(rem_farmers) >= 2 else rem_warriors
            if len(pool) >= 2:
                environment.assign_group(pool[0], "spawn warrior")
                environment.assign_group(pool[1], "spawn warrior")
                spawn_wheat -= 12
                rem_ids = {id(pool[0]), id(pool[1])}
                rem_farmers = [c for c in rem_farmers if id(c) not in rem_ids]
                rem_warriors = [c for c in rem_warriors if id(c) not in rem_ids]
        # Build up to 4 warriors aggressively
        elif total_warriors < 4 and spawn_wheat >= 12 and len(rem_farmers) >= 2:
            environment.assign_group(rem_farmers[0], "spawn warrior")
            environment.assign_group(rem_farmers[1], "spawn warrior")
            spawn_wheat -= 12
            rem_farmers = rem_farmers[2:]
        elif total_warriors < 4 and spawn_wheat >= 12 and len(rem_warriors) >= 2:
            environment.assign_group(rem_warriors[0], "spawn warrior")
            environment.assign_group(rem_warriors[1], "spawn warrior")
            spawn_wheat -= 12
            rem_warriors = rem_warriors[2:]
        # Maintain warrior count - spawn if low and wheat available
        elif total_warriors < 3 and spawn_wheat >= 12 and len(rem_farmers) + len(rem_warriors) >= 2:
            pool = rem_farmers + rem_warriors
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            spawn_wheat -= 12
            rem_ids = {id(pool[0]), id(pool[1])}
            rem_farmers = [c for c in rem_farmers if id(c) not in rem_ids]
            rem_warriors = [c for c in rem_warriors if id(c) not in rem_ids]

        # --- SEND WARRIORS TO CAVE ---
        # Strategy: keep at most 1 warrior in village as stagger buffer
        # Send rest to cave for immediate attack
        warriors_to_send = len(rem_warriors)
        keep_in_village = 1 if total_warriors >= 3 and warriors_to_send > 1 else 0

        for i, w in enumerate(rem_warriors):
            if i < warriors_to_send - keep_in_village:
                environment.assign_group(w, "cave")
            else:
                # Keep in village to farm (stagger buffer)
                environment.assign_group(w, "farm")

        # --- ASSIGN FARMERS ---
        # Keep minimum 2 farmers for wheat production; surplus goes to cave in late game
        min_farmers = 2 if dragon_hp > 30 else 1
        for i, f in enumerate(rem_farmers):
            if i < min_farmers:
                environment.assign_group(f, "farm")
            elif dragon_hp <= 30:
                # Late game: surplus farmers go attack (small but helps)
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            s_m = c.steps_since_meal

            if s_m >= 4:
                # HARD CONSTRAINT: must go to village now
                # Travel takes 1 step → arrive village at s_m=5 → eat next step
                # If they attack here, s_m→5, then travel→s_m=6, starving
                environment.assign_group(c, "village")
            elif dragon_hp <= 0:
                environment.assign_group(c, "village")
            else:
                # s_m in [0,3]: safe to attack (after attack, max s_m=4, still can travel+eat)
                environment.assign_group(c, "attack")