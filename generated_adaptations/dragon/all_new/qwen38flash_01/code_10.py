from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_w = list(environment.warriors)
        all_f = list(environment.farmers)
        total = len(all_w) + len(all_f)
        num_w = len(all_w)
        w_in_cave = sum(1 for w in all_w if w.location == "Cave")

        # Phase 1: Must eat (ssm >= 5, next step ssm=6 means starving)
        must_eat = []
        not_eat = []
        for c in components:
            if c.steps_since_meal >= 5:
                must_eat.append(c)
            else:
                not_eat.append(c)

        for c in must_eat:
            environment.assign_group(c, "eat")

        if not not_eat:
            return

        # Phase 2: Send warriors to cave if ssm <= 1 (they just ate or 1 step after)
        cave_ready_warriors = []
        still_in_village = []
        for c in not_eat:
            if c.role == "Warrior" and c.steps_since_meal <= 1:
                cave_ready_warriors.append(c)
            else:
                still_in_village.append(c)

        for c in cave_ready_warriors:
            environment.assign_group(c, "cave")

        # Phase 3: Spawn decisions
        # We want 3+ warriors attacking continuously
        # Meal reserve: each villager needs ~1 wheat per 6 steps, keep buffer
        meal_buffer = max(total, 5)
        spare_wheat = max(0, wheat - meal_buffer)

        spawn_group = []
        remaining = []
        for c in still_in_village:
            if len(spawn_group) < 2:
                spawn_group.append(c)
            else:
                remaining.append(c)

        # Decide if we should spawn
        need_spawn_warrior = False
        need_spawn_farmer = False

        if total < 5 and spare_wheat >= 10 and len(spawn_group) >= 2:
            # Under 5 villagers: spawn to grow population
            # Prefer warrior if few warriors, else farmer
            if num_w < 3 and spare_wheat >= 12:
                need_spawn_warrior = True
            else:
                need_spawn_farmer = True
        elif num_w == 0 and spare_wheat >= 12 and len(spawn_group) >= 2:
            need_spawn_warrior = True
        elif w_in_cave < 2 and num_w < 4 and spare_wheat >= 12 and len(spawn_group) >= 2:
            need_spawn_warrior = True
        elif total < 7 and w_in_cave >= 3 and spare_wheat >= 12 and len(spawn_group) >= 2:
            # Have enough attackers, grow more
            need_spawn_warrior = True

        if (need_spawn_warrior or need_spawn_farmer) and len(spawn_group) >= 2:
            if need_spawn_warrior:
                environment.assign_group(spawn_group[0], "spawn warrior")
                environment.assign_group(spawn_group[1], "spawn warrior")
            else:
                environment.assign_group(spawn_group[0], "spawn farmer")
                environment.assign_group(spawn_group[1], "spawn farmer")
            remaining_pool = spawn_group[2:] + remaining
        else:
            remaining_pool = spawn_group + remaining

        # Phase 4: Assign remaining villagers
        # Keep min farmers for wheat, send excess to cave in late game
        farmers_rem = [c for c in remaining_pool if c.role == "Farmer"]
        warriors_rem = [c for c in remaining_pool if c.role == "Warrior"]

        min_farm = 1 if total <= 3 else 2

        # Warriors remaining: send to cave if ssm allows, else farm
        for c in warriors_rem:
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Farmers: minimum farm for wheat, rest farm or go to cave late game
        for i, c in enumerate(farmers_rem):
            if i < min_farm:
                environment.assign_group(c, "farm")
            elif dragon_hp <= 40 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            elif dragon_hp <= 20:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Safety catch: assign any that slipped through
        for c in components:
            pass  # All should be covered above

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Must return to village NOW
                # Travel takes 1 step: ssm 4→5, arrive village, next step eat (ssm 5→0)
                # If we wait: ssm 5→travel→6 = starving
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")