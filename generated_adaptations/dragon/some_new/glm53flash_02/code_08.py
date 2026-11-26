from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        total = all_warriors + len(environment.farmers)

        # reserve wheat for meals this step
        hungry = sum(1 for c in components if c.steps_since_meal >= 4)
        wheat_for_spawns = wheat - hungry

        # aggressive warrior production: always keep growing the attack force
        spawn_slots = 0
        if wheat_for_spawns >= 12:
            if all_warriors < 6:
                spawn_slots = min(4, (wheat_for_spawns // 12) * 2)
            elif dragon.hp < 100 and wheat_for_spawns >= 40:
                spawn_slots = min(4, (wheat_for_spawns // 12) * 2)

        finishing = 0 < dragon.hp <= 40  # farmers help finish the dragon

        for c in components:
            # 1) eating has top priority (travel takes a step, so eat at >= 4)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                continue
            # 2) spawn warriors whenever possible (they are the main damage)
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) warriors attack: go to the cave
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                continue
            # 4) farmers: help finish the dragon, or occasionally grow the village
            if finishing and c.hp > 2 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
                continue
            if (c.role == "Farmer" and total < 6
                    and wheat_for_spawns >= 10 + 12 and c.hp > 3
                    and c.steps_since_meal <= 2 and step % 4 == 0):
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
            # otherwise attack (keep pressure so the dragon never regenerates)
            elif dragon.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")