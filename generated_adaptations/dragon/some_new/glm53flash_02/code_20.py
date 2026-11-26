from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")
        total = all_warriors + len(environment.farmers)

        hungry = sum(1 for c in components if c.steps_since_meal >= 5)
        wheat_for_spawns = wheat - hungry

        # decide spawn demand up front
        emergency = all_warriors == 0
        # early game: get offense started as soon as meals are covered
        want_warrior_pair = (wheat_for_spawns >= 12 and all_warriors < 4) or \
                            (wheat_for_spawns >= 22 and total < 16) or \
                            (emergency and wheat_for_spawns >= 12)
        want_farmer_pair = (not emergency and wheat_for_spawns >= 34
                            and total < 8 and step % 4 == 0)

        # larger squad for faster kill; everyone attacks at the endgame
        squad_size = 6
        finishing = 0 < dragon.hp <= 60
        if finishing:
            to_send = all_warriors  # every warrior goes
        else:
            to_send = max(0, squad_size - cave_warriors) if dragon.hp > 0 else 0

        assigned_spawn = 0
        for c in components:
            # 1) eating has top priority
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                continue
            # 2) emergency / regular warrior spawn: first claim on healthy bodies
            if want_warrior_pair and assigned_spawn < 2 and c.hp > 3:
                environment.assign_group(c, "spawn warrior")
                assigned_spawn += 1
                if assigned_spawn == 2:
                    want_warrior_pair = False
                    assigned_spawn = 0
                    wheat_for_spawns -= 12
                    want_farmer_pair = (not emergency
                                        and wheat_for_spawns >= 34
                                        and total < 8 and step % 4 == 0)
                continue
            # 3) grow the village when rich
            if want_farmer_pair and assigned_spawn < 2 and c.hp > 3:
                environment.assign_group(c, "spawn farmer")
                assigned_spawn += 1
                if assigned_spawn == 2:
                    want_farmer_pair = False
                    assigned_spawn = 0
                continue
            # 4) reinforce the attack squad (all warriors in endgame)
            if c.role == "Warrior" and c.hp > 1 and to_send > 0:
                environment.assign_group(c, "cave")
                to_send -= 1
                continue
            # 5) farmers: join the finishing assault, otherwise farm
            if finishing and c.hp > 2 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            # must leave now to eat in time (travel takes one step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            # too weak -> retreat
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            # otherwise attack (continuous pressure: no regeneration)
            elif dragon.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")