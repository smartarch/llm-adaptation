import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        nw = len(all_warriors)
        nf = len(all_farmers)
        total = nw + nf
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")

        assigned_ids = set()
        def do_assign(comp, group):
            cid = id(comp)
            if cid not in assigned_ids:
                assigned_ids.add(cid)
                environment.assign_group(comp, group)

        # Endgame: everyone rushes the cave
        if dragon_hp <= 35:
            for c in components:
                do_assign(c, "cave")
            return

        # Priority 1: Must eat (s_m >= 4 ensures safe rotation:
        # leave cave at s_m=3, travel(s_m=4), arrive village, eat(s_m=5->0). Safe.)
        for c in components:
            if c.steps_since_meal >= 4:
                do_assign(c, "eat")

        # Remaining villagers have s_m 0-3
        remaining = [c for c in components if id(c) not in assigned_ids]
        rem_warriors = [c for c in remaining if c.role == "Warrior"]
        rem_farmers = [c for c in remaining if c.role == "Farmer"]

        # All available warriors go to cave
        for w in rem_warriors:
            do_assign(w, "cave")

        # Farmer logic: spawn warriors, farm, and support cave
        # Determine spawn needs
        need_warrior_spawn = (nw == 0) or (nw < 3)
        need_pop_spawn = (total < 5)

        # Calculate how many farmer pairs we can spare for spawning
        # Need min_farm farmers farming for food production
        min_farm = 1
        if total < 3:
            min_farm = 1  # at least 1 farming if possible

        farm_list = []
        excess_farmers = []

        for f in rem_farmers:
            if len(farm_list) < min_farm:
                farm_list.append(f)
            else:
                excess_farmers.append(f)

        # Spawn warriors from excess farmers
        max_spawn_pairs = len(excess_farmers) // 2
        # Check wheat affordability: need 12 per pair + reserve of 1 wheat per villager
        reserve = max(total, 5)
        affordable = 0
        for p in range(1, max_spawn_pairs + 1):
            if wheat >= 12 * p + reserve:
                affordable = p
            else:
                break

        # If urgent need for warriors, be more aggressive with wheat
        if nw == 0 and max_spawn_pairs >= 1:
            for p in range(1, max_spawn_pairs + 1):
                if wheat >= 12 * p + 3:
                    affordable = max(affordable, p)
                else:
                    break

        # If total < 5, prioritize spawning over farming
        if total < 5 and max_spawn_pairs >= 1:
            affordable = max(affordable, 1)
            # Can also reduce min_farm to free up farmers for spawning
            if len(farm_list) > 0 and len(rem_farmers) >= 3:
                # Move 1 farmer from farm to excess for potential spawning
                moved = farm_list.pop()
                excess_farmers.insert(0, moved)
                # Recalculate max_spawn_pairs
                max_spawn_pairs = len(excess_farmers) // 2
                affordable = 0
                for p in range(1, max_spawn_pairs + 1):
                    if wheat >= 12 * p + 3:
                        affordable = p
                    else:
                        break

        actual_spawn_pairs = min(affordable, max_spawn_pairs)

        for i in range(actual_spawn_pairs * 2):
            do_assign(excess_farmers[i], "spawn warrior")

        # Remaining excess farmers: go to cave for backup DPS
        for i in range(actual_spawn_pairs * 2, len(excess_farmers)):
            do_assign(excess_farmers[i], "cave")

        # Farm assigned farmers
        for f in farm_list:
            do_assign(f, "farm")

        # Safety: if no warriors anywhere and no one sent to cave, send a farmer
        total_in_cave_soon = warriors_in_cave + len(rem_warriors) + actual_spawn_pairs  # rough estimate
        if nw + len(rem_warriors) == 0 and actual_spawn_pairs == 0:
            # No warriors exist and can't spawn. Someone must attack.
            for f in rem_farmers:
                if id(f) not in assigned_ids:
                    do_assign(f, "cave")
                    break

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # Endgame: attack regardless of hunger
            if dragon_hp <= 35:
                environment.assign_group(c, "attack")
            # Must leave to eat before starving
            # s_m=4 now: travel step -> s_m=5 in village (safe), eat next step -> s_m=0
            elif c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")