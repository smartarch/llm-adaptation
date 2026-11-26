from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")

        # reserve wheat for meals this step
        hungry = sum(1 for c in components if c.steps_since_meal >= 5)
        wheat_for_spawns = wheat - hungry

        # aggressive, uninterrupted warrior production
        # (attrition is high: the dragon eats warriors, so keep replacing them)
        spawn_slots = 0
        if wheat_for_spawns >= 12 and all_warriors < 12:
            spawn_slots = 2

        # small rotating squad: don't over-commit warriors to the dragon's wrath
        squad_size = 3
        to_send = max(0, squad_size - cave_warriors) if dragon.hp > 0 else 0

        farmers_farming = 0
        min_farmers = 2
        for c in components:
            # 1) eating has top priority
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                continue
            # 2) keep spawning warriors whenever wheat allows
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) keep the attack squad reinforced
            if c.role == "Warrior" and c.hp > 1 and to_send > 0:
                environment.assign_group(c, "cave")
                to_send -= 1
                continue
            # 4) everyone else (farmers and reserve warriors) farms
            if c.role == "Farmer" and farmers_farming >= min_farmers:
                pass  # fall through to farm below anyway
            farmers_farming += 1
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