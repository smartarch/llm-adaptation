from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)

        # 1) Feeding first: anyone at risk of starving eats now.
        to_feed = [c for c in components if c.steps_since_meal >= 4]
        fed = set()
        for c in to_feed:
            if wheat >= 1:
                groups["eat"].append(c)
                fed.add(id(c))
                wheat -= 1
            else:
                # No wheat -> keep them in village (farm) so they can eat later
                groups["farm"].append(c)
                fed.add(id(c))

        rest = [c for c in components if id(c) not in fed]

        # 2) Spawning: use surplus wheat to grow the population.
        spawning = set()
        # Farmers secure the food economy.
        if wheat >= 20 and n_farmers < 4 and len(rest) >= 2:
            groups["spawn farmer"].extend(rest[:2])
            spawning.update(id(c) for c in rest[:2])
            rest = rest[2:]
            wheat -= 10
        # Warriors speed up the kill.
        if wheat >= 32 and n_warriors < 8 and len(rest) >= 2:
            groups["spawn warrior"].extend(rest[:2])
            spawning.update(id(c) for c in rest[:2])
            rest = rest[2:]
            wheat -= 12

        # 3) Assign roles: warriors march to the Cave, farmers farm.
        farmers_rest = [c for c in rest if c.role == "Farmer"]
        warriors_rest = [c for c in rest if c.role == "Warrior"]

        # Keep enough farmers farming to sustain food; extra farmers can attack too.
        farmers_rest.sort(key=lambda c: -c.hp)
        n_farm_to_farm = 2
        for c in farmers_rest:
            if n_farm_to_farm > 0:
                groups["farm"].append(c)
                n_farm_to_farm -= 1
            else:
                groups["cave"].append(c)
        for c in warriors_rest:
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