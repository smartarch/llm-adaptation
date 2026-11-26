from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        all_alive = [v for v in environment.warriors + environment.farmers if v.hp > 0]
        in_cave = [v for v in all_alive if v.location == "Cave"]
        attackers_now = sum(1 for v in in_cave if v.steps_since_meal <= 3)

        assigned = {}

        # 1. MUST eat at sme >= 5
        for c in components:
            if c.steps_since_meal >= 5:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Endgame all-in: if total damage from all villagers >= dragon_hp, everyone attacks
        total_dmg = sum(3 if v.role == "Warrior" else 1 for v in in_cave if v.steps_since_meal <= 3)
        total_dmg += sum(3 if c.role == "Warrior" else 2 for c in remaining)
        if dragon_hp > 0 and total_dmg >= dragon_hp:
            for c in remaining:
                assigned[id(c)] = "cave"
            for c in components:
                if id(c) not in assigned:
                    assigned[id(c)] = "eat"
            for c in components:
                environment.assign_group(c, assigned[id(c)])
            return

        # 3. Spawn warriors aggressively (steps 1-8), using pairs
        spawn_w = []
        spawn_f = []
        n_warriors = sum(1 for v in environment.warriors if v.hp > 0)
        n_farmers = sum(1 for v in environment.farmers if v.hp > 0)

        if step <= 9 and wheat >= 14 and n_warriors < 8:
            # Use pairs of available villagers as spawners
            pool = [c for c in remaining if c.hp >= 2 and c.steps_since_meal <= 3]
            # Sort: prefer farmers as spawners (they produce less damage in cave)
            pool.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
            while len(pool) >= 4 and wheat >= 14 and n_warriors + len(spawn_w) // 2 < 8:
                spawner = [pool.pop(0), pool.pop(0)]
                spawn_w.extend(spawner)
                n_warriors += 1
                wheat -= 12

        for c in spawn_w:
            assigned[id(c)] = "spawn warrior"
        for c in spawn_f:
            assigned[id(c)] = "spawn farmer"

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Keep 1-2 farmers farming for wheat if wheat is low or dropping
        farmers_here = [c for c in remaining if c.role == "Farmer"]
        wheat_low = wheat < 10
        # Count how many farmers will still be farming if we send everyone to cave
        num_cave_ready = sum(1 for c in remaining if c.steps_since_meal <= 2 and c.hp >= 2)
        if wheat_low and len(farmers_here) >= 2:
            # Keep 1 farmer farming
            keep_farming = farmers_here[0]
            assigned[id(keep_farming)] = "farm"

        # 5. Send ALL fresh villagers to cave (sme <= 2, hp >= 2)
        for c in remaining:
            if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2:
                assigned[id(c)] = "cave"

        # 6. Everyone else farms
        for c in remaining:
            if id(c) not in assigned:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        assigned = {}

        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 1:
                assigned[id(c)] = "village"
            else:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])