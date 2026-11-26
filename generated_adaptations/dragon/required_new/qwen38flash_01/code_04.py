from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)

        # Separate by role and hunger
        hungry = []
        warriors_fresh = []  # sme <= 3, can go to cave
        warriors_mid = []    # sme == 4-5, need to eat
        farmers_list = []

        for c in components:
            if c.steps_since_meal >= 5:
                hungry.append(c)
            elif c.role == "Warrior":
                if c.steps_since_meal <= 3:
                    warriors_fresh.append(c)
                else:
                    warriors_mid.append(c)
            else:
                farmers_list.append(c)

        # --- Spawning logic (aggressive early) ---
        spawn_warrior_pool = []
        spawn_farmer_pool = []

        # Early game: aggressively spawn warriors
        if step <= 14 and dragon_hp > 0:
            # Need 2 spawners per warrior, cost 12 wheat
            # Use farmers as spawners if we have enough surplus
            # Keep at least 1 farmer farming if possible
            available_farmers_for_spawn = len(farmers_list)
            if step <= 6:
                # Very early: use pairs to spawn, sacrifice 1 farming step
                max_spawn_pairs = 2 if step <= 2 else 1
                while (available_farmers_for_spawn >= 2 and
                       wheat > 14 + len(hungry) + len(warriors_fresh) + 5 and
                       total_warriors < 6 and
                       len(spawn_warrior_pool) // 2 < max_spawn_pairs):
                    spawn_warrior_pool.append(farmers_list.pop(0))
                    spawn_warrior_pool.append(farmers_list.pop(0))
                    available_farmers_for_spawn -= 2
            elif step <= 10 and wheat > 30 and available_farmers_for_spawn >= 4:
                # Mid-early: spawn if well-resourced
                spawn_warrior_pool.append(farmers_list.pop(0))
                spawn_warrior_pool.append(farmers_list.pop(0))
                available_farmers_for_spawn -= 2

            # Spawn a farmer if very few farmers left
            if total_farmers < 2 and wheat >= 20 and len(farmers_list) >= 2:
                spawn_farmer_pool.append(farmers_list.pop(0))
                spawn_farmer_pool.append(farmers_list.pop(0))

        # --- Cave assignment ---
        cave_pool = []
        late_game = step >= 22

        if late_game:
            # All-in: send everyone who can fight
            for w in warriors_fresh:
                cave_pool.append(w)
            for w in warriors_mid:
                if w.steps_since_meal <= 4:
                    cave_pool.append(w)
            for f in farmers_list:
                if f.steps_since_meal <= 4 and len(cave_pool) < 3:
                    cave_pool.append(f)
            warriors_fresh = [w for w in warriors_fresh if w not in cave_pool]
            warriors_mid = [w for w in warriors_mid if w not in cave_pool]
            farmers_list = [f for f in farmers_list if f not in cave_pool]
        else:
            # Normal: send warriors to cave if they can sustain rotation
            # A warrior at sme <= 3 in village can travel + attack at sme=1,2,3
            # then return at sme=4, arrive village sme=5, eat
            for w in warriors_fresh:
                if w.hp >= 2:
                    cave_pool.append(w)
            warriors_fresh = [w for w in warriors_fresh if w not in cave_pool]

            # If very few warriors in cave, send farmers to help
            in_cave = sum(1 for v in environment.warriors + environment.farmers if v.location == "Cave")
            if in_cave < 2 and wheat > 20 and len(farmers_list) > 3:
                for f in farmers_list[:1]:
                    if f.steps_since_meal <= 2:
                        cave_pool.append(f)
                        farmers_list.remove(f)

        # --- Everyone else farms or eats ---
        farm_pool = farmers_list + warriors_fresh + warriors_mid

        # Execute assignments
        for c in hungry:
            environment.assign_group(c, "eat")
        for c in spawn_warrior_pool:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer_pool:
            environment.assign_group(c, "spawn farmer")
        for c in cave_pool:
            environment.assign_group(c, "cave")
        for c in farm_pool:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        late_game = step >= 22
        dragon_hp = environment.dragon.hp

        for c in components:
            # In late game, push through hunger if dragon is almost dead
            if late_game and dragon_hp <= 20:
                # All-in: only return if about to starve and would die
                if c.steps_since_meal >= 6:
                    environment.assign_group(c, "village")
                elif c.hp <= 1:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                # Must return to eat: sme>=4 means next step in village sme=5, eat safely
                if c.steps_since_meal >= 4:
                    environment.assign_group(c, "village")
                elif c.hp <= 1:
                    # Too damaged, retreat
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")