from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_villagers = list(environment.farmers) + list(environment.warriors)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]

        # Decide on a spawn pair (consumes 2 villagers for this step)
        spawn_pair = None
        if dragon_alive:
            if wheat >= 12 + 25 and len(warriors_here) >= 2:
                spawn_pair = ("spawn warrior", warriors_here[:2])
            elif wheat >= 12 + 25 and wheat >= 10 + 25 and len(farmers_here) >= 4:
                # Not enough warriors in village: sacrifice two farmers for warriors
                spawn_pair = ("spawn warrior", farmers_here[:2])
        # If population is critically low, prioritize reproducing farmers (food security)
        if spawn_pair is None and len(all_villagers) <= 3 and len(farmers_here) >= 2 \
                and wheat >= 10 + 15:
            spawn_pair = ("spawn farmer", farmers_here[:2])

        spawned = set()
        if spawn_pair is not None:
            spawned = set(id(c) for c in spawn_pair[1])

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_pair[0])
                continue
            # Eat in time (margin of 3 covers the 1-step trip back from the Cave),
            # or if too weak to be useful
            if c.steps_since_meal >= 3 or c.hp <= 1:
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Healthy warriors head out to attack the Dragon
                environment.assign_group(c, "cave")
            else:
                # Farmers keep the food economy running
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Retreat before starvation (arrive in Village at ssm 5, eat there),
            # or if too wounded to fight safely
            if c.steps_since_meal >= 4 or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")