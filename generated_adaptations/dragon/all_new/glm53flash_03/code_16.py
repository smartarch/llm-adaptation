import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        villagers = list(components)
        villagers.sort(key=lambda c: (c.steps_since_meal, 0 if c.role == "Warrior" else 1))

        assigned = set()
        endgame = dragon_hp <= 15  # no point building economy now

        # 1) eating: starving starts after 6 steps. Warriors need enough
        #    budget for a full round trip with 2 attacks, so they eat early.
        for c in villagers:
            if (c.role == "Warrior" and c.steps_since_meal >= 2) or c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        remaining = [c for c in villagers if id(c) not in assigned]
        # sprint dispatch: during the endgame any fresh warrior can go,
        # otherwise they need a counter <= 1 to fit 2 attacks + return
        warriors = [c for c in remaining
                    if c.role == "Warrior" and (c.steps_since_meal <= 1 or endgame)]
        farmers = [c for c in remaining if c.role == "Farmer"]

        total = len(environment.farmers) + len(environment.warriors)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)
        reserve = total + 2  # meals reserve so nobody ever starves from lack of wheat

        # 2) spawning (skipped only in the very endgame)
        spawn = None
        if not endgame:
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

        # 3) rest: warriors (with enough hunger budget) to the Cave, farmers farm
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
        for c in components:
            if c.steps_since_meal >= 4:
                # return now: arrive home at 5, eat before hitting 6
                environment.assign_group(c, "village")
            elif c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # farmers are weak attackers; send them home to farm
                environment.assign_group(c, "village")