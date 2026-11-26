from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        all_farmers = len(environment.farmers)

        # reserve wheat for meals this step (villagers eat at threshold 5 here)
        hungry = sum(1 for c in components if c.steps_since_meal >= 5)
        wheat_for_spawns = wheat - hungry

        # keep spawning warriors relentlessly while wheat allows
        spawn_slots = 0
        if wheat_for_spawns >= 12 and all_warriors < 8:
            spawn_slots = min(2, (wheat_for_spawns - 12) // 12 * 2 + 2)

        # economy guard: keep at least this many farmers on the farm
        min_farmers = 2

        farmers_committed = 0
        for c in components:
            # 1) eating (must eat before the counter reaches 6)
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                continue
            # 2) spawn warriors whenever wheat allows
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) all healthy warriors go attack
            if c.role == "Warrior" and c.hp > 1:
                environment.assign_group(c, "cave")
                continue
            # 4) farmers farm; spawn a farmer only if we can spare the economy
            if (c.role == "Farmer" and farmers_committed >= min_farmers
                    and wheat_for_spawns >= 22 and all_farmers < 5
                    and c.hp > 3 and c.steps_since_meal <= 2
                    and step % 5 == 0):
                environment.assign_group(c, "spawn farmer")
                farmers_committed += 0  # spawners still count as farmers present
                continue
            if c.role == "Farmer":
                farmers_committed += 1
                environment.assign_group(c, "farm")
            else:
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