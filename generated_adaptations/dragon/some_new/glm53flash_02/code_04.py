from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        n_villagers = len(environment.warriors) + len(environment.farmers)
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")
        all_warriors = len(environment.warriors)

        # send warriors to the cave while the dragon is engaged
        wanted_in_cave = 4
        to_send = wanted_in_cave - cave_warriors if dragon.hp < 100 else 0

        # if no warriors exist at all, spawn some
        need_warriors = all_warriors == 0 or (dragon.hp < 100 and all_warriors < 3)
        spawn_budget = 2 if need_warriors else (2 if (wheat > 60 and step % 6 == 0) else 0)

        spawn_slots = 0
        for c in components:
            # 1) eating has top priority (travel takes a step, so eat at >= 4)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                continue
            # 2) spawn warriors when needed (healthy, fed villagers)
            if spawn_slots < spawn_budget and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots += 1
                continue
            # 3) send warriors to the cave to attack
            if c.role == "Warrior" and to_send > 0:
                environment.assign_group(c, "cave")
                to_send -= 1
                continue
            # 4) default: farm
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            # starving or nearly starving -> go home to eat (travel takes one step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            # too weak -> retreat
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            # otherwise attack (dragon must die as fast as possible)
            elif dragon.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")