from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)
        total = n_farmers + n_warriors
        reserve = total  # keep one meal per villager as reserve

        assigned = set()

        # 1) Feeding first: anyone at risk of starving eats now.
        to_feed = [c for c in components if c.steps_since_meal >= 4]
        for c in to_feed:
            if wheat >= 1:
                groups["eat"].append(c)
                wheat -= 1
            else:
                groups["farm"].append(c)
            assigned.add(id(c))

        rest = [c for c in components if id(c) not in assigned]

        # 2) Aggressive spawning: warriors are the key to a fast kill.
        def take(pair, group, cost):
            nonlocal wheat
            groups[group].extend(pair)
            for c in pair:
                assigned.add(id(c))
            wheat -= cost

        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # Spawn warriors whenever affordable (reserve one meal per villager).
        if wheat >= 12 + reserve and len(rest) >= 2 and n_warriors < 10:
            pair = (warriors_here + farmers_here + rest)[:2]
            take(pair, "spawn warrior", 12)
        # Grow the population / food economy with farmers early on.
        elif total < 5 and wheat >= 10 + reserve and len(rest) >= 2:
            pair = (farmers_here + rest)[:2]
            take(pair, "spawn farmer", 10)

        rest = [c for c in components if id(c) not in assigned]
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # 3) Warriors march to the Cave; farmers farm (2) or reinforce the Cave.
        for c in warriors_here:
            groups["cave"].append(c)
        farmers_here.sort(key=lambda c: -c.hp)
        for i, c in enumerate(farmers_here):
            if i < 2:
                groups["farm"].append(c)
            else:
                groups["cave"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}

        for c in components:
            # Starving villagers are too weak to damage the Dragon;
            # send them (and those about to starve) home to eat.
            if c.steps_since_meal >= 4 or c.hp <= 1:
                groups["village"].append(c)
            else:
                groups["attack"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)