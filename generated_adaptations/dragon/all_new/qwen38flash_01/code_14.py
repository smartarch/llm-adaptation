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

        # Build assignment for each component
        assignments = {}  # id(c) -> group

        # Phase 1: Must eat (ssm >= 5)
        for c in components:
            if c.steps_since_meal >= 5:
                assignments[id(c)] = "eat"

        # Phase 2: Warriors with ssm <= 1 go to cave
        for c in components:
            if id(c) not in assignments and c.role == "Warrior" and c.steps_since_meal <= 1:
                assignments[id(c)] = "cave"

        # Phase 3: Spawning decisions
        # Get unassigned components
        unassigned = [c for c in components if id(c) not in assignments]
        farmers_un = [c for c in unassigned if c.role == "Farmer"]
        warriors_un = [c for c in unassigned if c.role == "Warrior"]

        # Keep min farmers for wheat
        min_farm = 1 if total <= 3 else 2
        farmers_for_farm = farmers_un[:min_farm]
        farmers_for_spawn = farmers_un[min_farm:]

        # Spawn pool: extra farmers + idle warriors (ssm >= 3 can't go to cave usefully)
        spawn_pool = list(farmers_for_spawn) + [c for c in warriors_un if c.steps_since_meal >= 3]

        # Decide spawning
        # Need spawn_cost + total for meal reserve
        if total < 5 and len(spawn_pool) >= 2:
            if num_w < 4 and wheat >= 12 + total:
                for i in range(min(2, len(spawn_pool) // 2)):
                    c1 = spawn_pool.pop(0)
                    c2 = spawn_pool.pop(0)
                    assignments[id(c1)] = "spawn warrior"
                    assignments[id(c2)] = "spawn warrior"
            elif wheat >= 10 + total:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                assignments[id(c1)] = "spawn farmer"
                assignments[id(c2)] = "spawn farmer"
        elif (num_w == 0 or w_in_cave < 2) and wheat >= 12 + total and len(spawn_pool) >= 2:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            assignments[id(c1)] = "spawn warrior"
            assignments[id(c2)] = "spawn warrior"
        elif num_w < 6 and w_in_cave < 3 and wheat >= 12 + total + 5 and len(spawn_pool) >= 2:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            assignments[id(c1)] = "spawn warrior"
            assignments[id(c2)] = "spawn warrior"

        # Phase 4: Assign remaining warriors
        # Those with ssm <= 2 go to cave, others farm
        for c in warriors_un:
            if id(c) not in assignments:
                if c.steps_since_meal <= 2:
                    assignments[id(c)] = "cave"
                else:
                    assignments[id(c)] = "farm"

        # Phase 5: Assign farmers
        for c in farmers_for_farm:
            if id(c) not in assignments:
                assignments[id(c)] = "farm"

        # Extra farmers: farm normally, go to cave only if wheat is abundant and dragon low
        wheat_surplus = wheat - total  # rough surplus after one meal per villager
        for c in spawn_pool:
            if id(c) not in assignments:
                if dragon_hp <= 15 and wheat_surplus >= 15:
                    assignments[id(c)] = "cave"
                else:
                    assignments[id(c)] = "farm"

        # Execute all assignments
        for c in components:
            if id(c) in assignments:
                environment.assign_group(c, assignments[id(c)])
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