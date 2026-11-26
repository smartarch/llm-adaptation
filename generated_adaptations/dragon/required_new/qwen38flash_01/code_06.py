from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        late_game = step >= 22

        # Count villagers currently in cave who can still attack
        all_villagers = environment.warriors + environment.farmers
        in_cave = [v for v in all_villagers if v.location == "Cave"]
        in_cave_can_attack = sum(
            1 for v in in_cave
            if v.steps_since_meal < 5 and v.hp > 1
        )

        # Categorize villagers in village
        eat_list = []
        to_cave = []
        spawn_w_pool = []
        spawn_f_pool = []
        farm_list = []

        warriors_here = [c for c in components if c.role == "Warrior"]
        farmers_here = [c for c in components if c.role == "Farmer"]
        others = [c for c in components if c.role not in ("Warrior", "Farmer")]

        # Step 1: anyone hungry eats
        hungry = [c for c in components if c.steps_since_meal >= 4]
        not_hungry = [c for c in components if c.steps_since_meal < 4]
        for c in hungry:
            eat_list.append(c)

        # Re-filter warriors and farmers from not_hungry
        warriors_nh = [c for c in not_hungry if c.role == "Warrior"]
        farmers_nh = [c for c in not_hungry if c.role == "Farmer"]

        # Step 2: Late game all-in
        if late_game:
            for c in warriors_nh:
                to_cave.append(c)
            for c in farmers_nh:
                if c.hp >= 2:
                    to_cave.append(c)
            warriors_nh = []
            farmers_nh = []

        # Step 3: Spawn warriors aggressively early
        remaining_wheat_after_food = wheat
        # Estimate wheat needed for eating this step
        eat_cost = len(eat_list)
        remaining_wheat_after_food -= eat_cost

        # Also account for wheat that will be needed soon (villagers in cave arriving hungry)
        urgent_eat = sum(1 for v in in_cave if v.steps_since_meal >= 3)
        remaining_wheat_after_food -= urgent_eat

        if step < 12 and not late_game:
            # Aggressive warrior spawning early
            while (len(farmers_nh) >= 2 and
                   remaining_wheat_after_food >= 12 and
                   len(spawn_w_pool) < 2):
                # Keep at least 1 farmer farming if possible
                if len(farmers_nh) <= 2 and remaining_wheat_after_food < 20:
                    break
                spawn_w_pool.append(farmers_nh.pop(0))
                spawn_w_pool.append(farmers_nh.pop(0))
                remaining_wheat_after_food -= 12
                in_cave_can_attack  # just referencing to not get optimized out

            # Spawn farmer if very few
            total_farmers = len([v for v in all_villagers if v.role == "Farmer"])
            if total_farmers < 2 and len(farmers_nh) >= 2 and remaining_wheat_after_food >= 10:
                spawn_f_pool.append(farmers_nh.pop(0))
                spawn_f_pool.append(farmers_nh.pop(0))
                remaining_wheat_after_food -= 10

        # Step 4: Send warriors/farmers to cave (staggered)
        if not late_game:
            # Target: keep 2-3 attackers in cave at all times
            target_in_cave = 3 if step > 5 else 2

            # Send warriors first
            send_count = 0
            max_send = max(0, target_in_cave - in_cave_can_attack)

            for c in warriors_nh:
                if send_count >= max_send:
                    break
                if c.hp >= 2:
                    to_cave.append(c)
                    send_count += 1

            warriors_nh = [c for c in warriors_nh if c not in to_cave]

            # If still no one in cave who can attack, send a farmer
            in_cave_can_attack_new = in_cave_can_attack + send_count
            if in_cave_can_attack_new == 0 and len(farmers_nh) > 1:
                for f in farmers_nh:
                    if f.steps_since_meal <= 2:
                        to_cave.append(f)
                        farmers_nh.remove(f)
                        break

            # Mid-game: send extra warriors if wheat is plentiful
            if (step >= 4 and step < 20 and
                    remaining_wheat_after_food > 30 and
                    in_cave_can_attack_new < 2):
                for c in warriors_nh:
                    if c.steps_since_meal <= 2:
                        to_cave.append(c)
                        warriors_nh.remove(c)
                        break

        # Step 5: Everyone remaining farms
        farm_list = warriors_nh + farmers_nh + others

        # Execute all assignments
        for c in eat_list:
            environment.assign_group(c, "eat")
        for c in spawn_w_pool:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_f_pool:
            environment.assign_group(c, "spawn farmer")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farm_list:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        late_game = step >= 22

        for c in components:
            sme = c.steps_since_meal
            hp = c.hp

            # Critical: must return to eat before starving
            if sme >= 6:
                environment.assign_group(c, "village")
                continue

            # Warriors can push to sme=5 (arrive village sme=6, eat, lose 1 HP)
            # Farmers safer at sme=4 (arrive village sme=5, eat, no HP loss)
            # But in late game, push harder
            if late_game:
                if sme >= 6 or hp <= 1:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                if c.role == "Warrior":
                    # Attack sme 1,2,3,4 then return (arrive sme=5, eat)
                    if sme >= 5 or hp <= 1:
                        environment.assign_group(c, "village")
                    else:
                        environment.assign_group(c, "attack")
                else:
                    # Farmer: attack sme 1,2,3 then return (arrive sme=4, eat)
                    if sme >= 4 or hp <= 1:
                        environment.assign_group(c, "village")
                    else:
                        environment.assign_group(c, "attack")