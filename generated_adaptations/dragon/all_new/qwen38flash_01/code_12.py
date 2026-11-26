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

        # Phase 1: Must eat (ssm >= 5 means next step would be 6 = starve)
        must_eat = [c for c in components if c.steps_since_meal >= 5]
        not_eat = [c for c in components if c.steps_since_meal < 5]
        for c in must_eat:
            environment.assign_group(c, "eat")

        if not not_eat:
            return

        # Phase 2: Warriors with ssm <= 1 go to cave immediately (just ate)
        cave_ready = [c for c in not_eat if c.role == "Warrior" and c.steps_since_meal <= 1]
        in_village = [c for c in not_eat if c not in cave_ready]
        for c in cave_ready:
            environment.assign_group(c, "cave")

        # Phase 3: Spawning logic
        # Meal reserve: everyone needs ~1 wheat per 6 steps, keep buffer
        meal_reserve = max(total + 2, 5)
        spare = max(0, wheat - meal_reserve)

        # Split remaining by role
        farmers_v = [c for c in in_village if c.role == "Farmer"]
        warriors_v = [c for c in in_village if c.role == "Warrior"]

        # Min farmers to keep farming (need at least 1-2 for wheat production)
        min_farm = 1 if total <= 4 else 2
        farmers_farm = farmers_v[:min_farm]
        farmers_extra = farmers_v[min_farm:]

        # Spawn pool: extra farmers + idle warriors (ssm >= 2 can't go to cave usefully now)
        idle_warriors = [c for c in warriors_v if c.steps_since_meal >= 2]
        go_cave_warriors = [c for c in warriors_v if c.steps_since_meal <= 1]
        spawn_pool = list(farmers_extra) + list(idle_warriors)

        # Decide spawning
        spawned = set()
        should_spawn_warrior = False
        should_spawn_farmer = False

        if total < 5:
            # Always grow population when under 5
            if spare >= 12 and num_w < 4:
                should_spawn_warrior = True
            elif spare >= 10:
                should_spawn_farmer = True
        elif num_w == 0 and spare >= 12:
            should_spawn_warrior = True
        elif w_in_cave < 3 and num_w < 6 and spare >= 12:
            should_spawn_warrior = True
        elif w_in_cave >= 3 and num_w < 8 and spare >= 12 and total < 10:
            should_spawn_warrior = True
        elif total < 8 and spare >= 10:
            should_spawn_farmer = True

        if (should_spawn_warrior or should_spawn_farmer) and len(spawn_pool) >= 2:
            if should_spawn_warrior:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
            else:
                environment.assign_group(spawn_pool[0], "spawn farmer")
                environment.assign_group(spawn_pool[1], "spawn farmer")
            spawned.add(id(spawn_pool[0]))
            spawned.add(id(spawn_pool[1]))

        # Phase 4: Assign all remaining
        for c in components:
            if id(c) in [id(x) for x in must_eat]:
                continue  # already assigned to eat
            if id(c) in [id(x) for x in cave_ready]:
                continue  # already assigned to cave
            if id(c) in spawned:
                continue  # already assigned to spawn

            if c.role == "Warrior":
                if c.steps_since_meal <= 1:
                    environment.assign_group(c, "cave")
                elif c.steps_since_meal <= 2:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

            elif c.role == "Farmer":
                # Check if we have surplus wheat to spare a farmer
                # Only send to cave if wheat is plentiful AND dragon is nearly dead
                wheat_surplus = spare - (total - len(must_eat))
                if dragon_hp <= 20 and wheat_surplus >= 10:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")