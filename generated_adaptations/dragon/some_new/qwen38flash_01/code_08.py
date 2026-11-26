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

        # Estimate meals needed in next 1-2 steps from villagers in cave
        upcoming_meals = 0
        for w in all_warriors:
            if w.location == "Cave" and w.steps_since_meal >= 3:
                upcoming_meals += 1
        for f in all_farmers:
            if f.location == "Cave" and f.steps_since_meal >= 3:
                upcoming_meals += 1
        # Villagers in village approaching meal time
        near_meals = sum(1 for c in components if c.steps_since_meal >= 2)
        wheat_reserve = upcoming_meals + near_meals

        # Feed hungry villagers (s_m >= 3)
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)

        for c in hungry:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Remaining villagers (s_m < 3)
        remaining = [c for c in components if c.steps_since_meal < 3]
        rem_farmers = [c for c in remaining if c.role == "Farmer"]
        rem_warriors = [c for c in remaining if c.role == "Warrior"]

        # --- SPAWNING LOGIC ---
        # Critical: no warriors at all -> spawn immediately using any 2 villagers
        if total_warriors == 0:
            pool = rem_farmers + rem_warriors
            if len(pool) >= 2 and wheat >= 12:
                environment.assign_group(pool[0], "spawn warrior")
                environment.assign_group(pool[1], "spawn warrior")
                wheat -= 12
                ids = {id(pool[0]), id(pool[1])}
                rem_farmers = [c for c in rem_farmers if id(c) not in ids]
                rem_warriors = [c for c in rem_warriors if id(c) not in ids]
            elif len(pool) >= 2:
                # Can't spawn, just farm
                for c in pool:
                    environment.assign_group(c, "farm")
                return
            else:
                for c in pool:
                    environment.assign_group(c, "farm")
                return
        # Spawn warriors aggressively if small population and wheat allows
        elif total_villagers < 5 and wheat - wheat_reserve >= 12:
            if len(rem_farmers) >= 2:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_farmers[1], "spawn warrior")
                wheat -= 12
                rem_farmers = rem_farmers[2:]
            elif len(rem_warriors) >= 2:
                environment.assign_group(rem_warriors[0], "spawn warrior")
                environment.assign_group(rem_warriors[1], "spawn warrior")
                wheat -= 12
                rem_warriors = rem_warriors[2:]
        # Continue spawning up to 4 warriors if wheat is abundant
        elif total_warriors < 4 and wheat - wheat_reserve >= 14:
            if len(rem_farmers) >= 2:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_farmers[1], "spawn warrior")
                wheat -= 12
                rem_farmers = rem_farmers[2:]
            elif len(rem_warriors) >= 2:
                environment.assign_group(rem_warriors[0], "spawn warrior")
                environment.assign_group(rem_warriors[1], "spawn warrior")
                wheat -= 12
                rem_warriors = rem_warriors[2:]

        # --- SEND ALL AVAILABLE WARRIORS TO CAVE ---
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- ASSIGN FARMERS ---
        # Keep enough farmers to sustain wheat production
        min_farm = max(1, (total_villagers + 4) // 5)
        for f in rem_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave NOW: travel 1 step, arrive at s_m=5, eat next step
                # If we wait until s_m=5, they'd arrive at s_m=6 and starve
                environment.assign_group(c, "village")
            else:
                # s_m < 4: safe to attack (at most 3 more steps before must leave)
                environment.assign_group(c, "attack")