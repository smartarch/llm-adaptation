from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)
        total_pop = len(all_warriors) + len(all_farmers)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]

        # Villagers that must eat this step (they take priority over anything else)
        hungry = [c for c in components if c.steps_since_meal >= 3 or c.hp <= 1]

        # Decide on a spawn pair, but only with a large safety buffer so that
        # spawning can never jeopardize feeding everyone.
        spawn_group, spawn_pair = None, None
        if dragon_alive:
            if len(all_warriors) >= 2 and wheat >= 12 + 40 + len(hungry):
                spawn_group, spawn_pair = "spawn warrior", warriors_here[:2]
            elif len(all_warriors) == 0 and len(farmers_here) >= 2 \
                    and wheat >= 12 + 40 + len(hungry):
                # Emergency: no warriors at all -> convert two farmers,
                # otherwise we can never kill the Dragon.
                spawn_group, spawn_pair = "spawn warrior", farmers_here[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif c.steps_since_meal >= 3 or c.hp <= 1:
                # Eat with a 2-step safety margin before the 6-step limit
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Healthy warriors head out to attack the Dragon
                environment.assign_group(c, "cave")
            else:
                # Farmers keep producing wheat
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Retreat early enough: arriving in the Village with
            # steps_since_meal == 4 leaves 2 steps of safety margin,
            # since they eat immediately upon arrival.
            if c.steps_since_meal >= 3 or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")