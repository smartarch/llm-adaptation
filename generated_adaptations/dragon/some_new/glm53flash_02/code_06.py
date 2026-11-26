from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)

        # wheat that must be reserved for eating this step
        hungry = [c for c in components if c.steps_since_meal >= 4]
        wheat_for_spawns = wheat - len(hungry)

        # how many warriors may be spawned this step (2 per spawn, 12 wheat each)
        max_spawns = max(0, int(wheat_for_spawns // 12)) if wheat_for_spawns >= 12 else 0
        want_warriors = all_warriors < 5 or dragon.hp < 100
        spawn_slots = min(max_spawns, 4) if want_warriors else 0

        for c in components:
            # 1) eating has top priority (travel takes a step, so eat at >= 4)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                continue
            # 2) spawn warriors while we need more offense
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) send every available warrior to attack
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                continue
            # 4) farmers farm (or occasionally spawn more farmers when rich)
            if (c.role == "Farmer" and wheat >= 10 + 2 * len(hungry)
                    and len(environment.farmers) + len(environment.warriors) < 5
                    and c.hp > 3 and c.steps_since_meal <= 2
                    and step % 5 == 0):
                environment.assign_group(c, "spawn farmer")
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            # starving -> go home to eat (travel takes one step)
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