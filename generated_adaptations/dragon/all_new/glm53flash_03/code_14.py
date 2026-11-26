import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        villagers = list(components)
        villagers.sort(key=lambda c: (c.steps_since_meal, 0 if c.role == "Warrior" else 1))

        assigned = set()
        sprint = dragon_hp <= 40  # endgame: kill fast, food scheduling can slip

        # 1) eating: starving starts after 6 steps. Warriors normally need
        #    enough budget for a full round trip with 2 attacks, so they eat
        #    early. During the sprint, only truly urgent eating happens.
        for c in villagers:
            if sprint:
                if c.steps_since_meal >= 4:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
            elif (c.role == "Warrior" and c.steps_since_meal >= 2) or c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        remaining = [c for c in villagers if id(c) not in assigned]
        warriors = [c for c in remaining if c.role == "Warrior"]
        if not sprint:
            warriors = [c for c in warriors if c.steps_since_meal <= 1]
        farmers = [c for c in remaining if c.role == "Farmer"]

        total = len(environment.farmers) + len(environment.warriors)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)
        reserve = total + 2  # meals reserve so nobody ever starves from lack of wheat

        # 2) spawning (skipped during the sprint — just kill it now)
        spawn = None
        if not sprint:
            if warrior_count == 0 and wheat >= 12 + reserve and len(remaining) >= 2:
                spawn = ("spawn warrior", remaining[:2])
            elif wheat >= 12 + reserve and len(remaining) >= 2 and total < 12:
                pool = warriors if len(warriors) >= 2 else farmers
                if len(pool) >= 2:
                    spawn = ("spawn warrior", pool[:2])
            elif wheat >= 10 + reserve and farmer_count < 4 and len(farmers) >= 2:
                spawn = ("spawn farmer", farmers[:2])

        if spawn:
            name, pair = spawn
            for c in pair:
                environment.assign_group(c, name)
                assigned.add(id(c))

        # 3) rest: warriors to the Cave, farmers farm
        cave_set = {id(c) for c in warriors}
        for c in remaining:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and id(c) in cave_set:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(id(c))

        # safety: every component assigned exactly once
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "eat")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        sprint = dragon_hp <= 40
        for c in components:
            # sprint: keep everyone attacking as long as they can't starve yet
            if c.steps_since_meal >= (5 if sprint else 4):
                # return now: arrive home in time to eat before starving
                environment.assign_group(c, "village")
            elif c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # farmers are weak attackers; send them home to farm
                environment.assign_group(c, "village")