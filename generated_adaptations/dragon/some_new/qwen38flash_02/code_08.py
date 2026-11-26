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
        num_warriors = len(all_warriors)
        num_farmers = len(all_farmers)
        total = num_warriors + num_farmers

        # Count who's in cave
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in all_farmers if f.location == "Cave")
        attackers_in_cave = warriors_in_cave + farmers_in_cave

        # Endgame: send everyone to cave to attack
        if dragon_hp <= 40:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # Separate by role and hunger
        must_eat = []
        fresh_farmers = []
        fresh_warriors = []
        hungry_fresh = []  # steps 3-4, need to plan ahead

        for c in components:
            if c.steps_since_meal >= 5:
                must_eat.append(c)
            elif c.steps_since_meal >= 3:
                hungry_fresh.append(c)
            elif c.role == "Farmer":
                fresh_farmers.append(c)
            else:
                fresh_warriors.append(c)

        # 1) Must eat
        for c in must_eat:
            environment.assign_group(c, "eat")

        # 2) Hungry (steps 3-4): eat to be safe
        for c in hungry_fresh:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
            else:
                # step 3: can still do one more step
                if c.role == "Farmer":
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, "farm")

        # 3) Spawn warriors aggressively
        # Priority: spawn warriors whenever we have 2+ fresh farmers and enough wheat
        # Keep at least 1 farmer farming
        min_farming = 1
        spawn_pool = []
        farm_list = []

        for i, f in enumerate(fresh_farmers):
            if len(farm_list) < min_farming:
                farm_list.append(f)
            else:
                spawn_pool.append(f)

        # Spawn as many warriors as possible from spawn_pool
        # Reserve wheat: need 1 wheat per villager for future meals
        # Be aggressive: just need 12 per pair + small reserve
        reserve = max(total, 5)  # ensure food security
        max_spawn_pairs = 0
        for p in range(1, len(spawn_pool) // 2 + 1):
            if wheat >= 12 * p + reserve:
                max_spawn_pairs = p
            else:
                break

        # If no warriors exist, be very aggressive about spawning
        if num_warriors == 0 and len(spawn_pool) >= 2:
            # Use all spare farmers for spawning even if tight on wheat
            max_spawn_pairs = max(max_spawn_pairs, len(spawn_pool) // 2)
            # Recalculate with lower reserve
            reserve = 3
            for p in range(1, len(spawn_pool) // 2 + 1):
                if wheat >= 12 * p + reserve:
                    max_spawn_pairs = p
                else:
                    break

        for i in range(max_spawn_pairs * 2):
            environment.assign_group(spawn_pool[i], "spawn warrior")
        for i in range(max_spawn_pairs * 2, len(spawn_pool)):
            environment.assign_group(spawn_pool[i], "farm")
            farm_list.append(spawn_pool[i])

        # 4) Farm remaining farmers
        for f in farm_list:
            environment.assign_group(f, "farm")

        # 5) Send fresh warriors to cave (staggered: only send those truly fresh)
        # Count how many warriors are already in cave to avoid over-sending
        # Only send if we don't already have enough attackers
        # Stagger: if 2+ fresh warriors, send only half to stagger their hunger cycles
        if num_warriors == 0 or warriors_in_cave < 2:
            # Urgent: send all fresh warriors to cave
            for w in fresh_warriors:
                environment.assign_group(w, "cave")
        else:
            # Stagger: send at most ceil(len/2) fresh warriors to cave
            num_to_send = (len(fresh_warriors) + 1) // 2
            for i in range(num_to_send):
                environment.assign_group(fresh_warriors[i], "cave")
            # Others stay in village (farm to maintain food, will go after eating cycle)
            for i in range(num_to_send, len(fresh_warriors)):
                environment.assign_group(fresh_warriors[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # Endgame: everyone attacks regardless of hunger
            if dragon_hp <= 40:
                environment.assign_group(c, "attack")
            # About to starve: must leave now
            # At steps_since_meal=4, if we attack this step, next step it's 5.
            # Step after that it's 6 = starving. So leave at 4 to be safe.
            # Travel 1 step (arrive village at s_m=5), eat next step (safe).
            elif c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")