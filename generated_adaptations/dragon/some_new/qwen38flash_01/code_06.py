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
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in all_farmers if f.location == "Cave")
        total_warriors = len(all_warriors)

        # Categorize components
        urgent_feed = []
        others = []
        for c in components:
            if c.steps_since_meal >= 3:
                urgent_feed.append(c)
            else:
                others.append(c)
        urgent_feed.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # Assign urgent feed
        for c in urgent_feed:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Separate remaining by role
        rem_farmers = [c for c in others if c.role == "Farmer"]
        rem_warriors = [c for c in others if c.role == "Warrior"]

        # --- SPAWN LOGIC ---
        # Critical: no warriors at all -> spawn immediately
        if total_warriors == 0:
            pool = rem_farmers + rem_warriors
            if len(pool) >= 2 and wheat >= 12:
                environment.assign_group(pool[0], "spawn warrior")
                environment.assign_group(pool[1], "spawn warrior")
                wheat -= 12
                rem_farmers = [c for c in rem_farmers if c not in (pool[0], pool[1])]
                rem_warriors = [c for c in rem_warriors if c not in (pool[0], pool[1])]
            elif len(pool) >= 2:
                # Not enough wheat, farm instead
                for c in pool:
                    environment.assign_group(c, "farm")
                return

        # Spawn warriors aggressively if population is small and we have wheat
        elif total_villagers < 6 and wheat >= 12 and len(rem_farmers) >= 2:
            environment.assign_group(rem_farmers[0], "spawn warrior")
            environment.assign_group(rem_farmers[1], "spawn warrior")
            wheat -= 12
            rem_farmers = rem_farmers[2:]
        elif total_villagers < 6 and wheat >= 12 and len(rem_warriors) >= 2:
            environment.assign_group(rem_warriors[0], "spawn warrior")
            environment.assign_group(rem_warriors[1], "spawn warrior")
            wheat -= 12
            rem_warriors = rem_warriors[2:]

        # --- SEND WARRIORS TO CAVE ---
        for w in rem_warriors:
            environment.assign_group(w, "cave")
        rem_warriors = []

        # --- FARMERS: farm, or go to cave in late game ---
        min_farm = max(2, (total_villagers + 4) // 5)
        farmed = 0
        for f in rem_farmers:
            if farmed < min_farm:
                environment.assign_group(f, "farm")
                farmed += 1
            elif dragon_hp <= 20:
                # Late game: surplus farmers go to cave for extra damage
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")
                farmed += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            s_m = c.steps_since_meal

            if dragon_hp <= 0:
                # Dragon dead, go home
                environment.assign_group(c, "village")
            elif s_m >= 5:
                # Must leave: attack worked at s_m=5 this step (if we assign attack),
                # but next step they can't attack. Better to go now.
                # At s_m=5, send to village: travel (s_m=6), arrive village, eat next step.
                # Loses 1 HP but saves the position.
                environment.assign_group(c, "village")
            elif s_m >= 4:
                # s_m=4: can still attack (4 < 6). Attack one more time then go.
                environment.assign_group(c, "attack")
            else:
                # s_m < 4: attack
                environment.assign_group(c, "attack")