import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        ids = {g: i for i, g in enumerate(group_ids)}
        wheat = environment.farm.wheat
        total = len(environment.farmers) + len(environment.warriors)
        villagers = list(components)

        # sort: hungriest first, warriors before farmers (warriors are more useful)
        villagers.sort(key=lambda c: (c.steps_since_meal, 0 if c.role == "Warrior" else 1))

        used = set()
        # 1) eat: anyone about to starve (starves at 6, eat at 5)
        for c in villagers:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, ids["eat"])
                used.add(id(c))

        remaining = [c for c in villagers if id(c) not in used]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # 2) spawning: needs pairs, plenty of wheat, and never touches starving villagers
        spawn_pairs = []
        # warriors are the priority for killing fast, but keep some farmers for wheat
        if wheat >= 24 and len(farmers) >= 2:
            spawn_pairs = [("spawn warrior", farmers[:2])]
            farmers = farmers[2:]
        elif wheat >= 24 and len(warriors) >= 2 and len(farmers) >= 3:
            spawn_pairs = [("spawn warrior", warriors[:2])]
            warriors = warriors[2:]
        elif wheat >= 20 and total <= 6 and len(remaining) >= 4:
            pair = (remaining[:2])
            spawn_pairs = [("spawn farmer", pair)]
            remaining_ids = {id(c) for c in pair}
            warriors = [c for c in warriors if id(c) not in remaining_ids]
            farmers = [c for c in farmers if id(c) not in remaining_ids]

        for name, pair in spawn_pairs:
            for c in pair:
                environment.assign_group(c, ids[name])

        # 3) everyone else: warriors to the cave, farmers to the farm
        for c in remaining:
            if id(c) in {id(p) for pair_ in spawn_pairs for p in pair_}:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, ids["cave"])
            else:
                environment.assign_group(c, ids["farm"])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        ids = {g: i for i, g in enumerate(group_ids)}
        for c in components:
            if c.steps_since_meal >= 3:
                # leave time to travel back and eat before starving (6)
                environment.assign_group(c, ids["village"])
            elif c.role == "Warrior":
                environment.assign_group(c, ids["attack"])
            else:
                # farmers are weak attackers and just waste food/HP -> send home
                environment.assign_group(c, ids["village"])