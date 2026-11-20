import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers in the Village eat once they have gone this many steps without food.
    VILLAGE_EAT_THRESHOLD = 3
    # Villagers in the Cave return to the Village once they reach this many steps without food.
    CAVE_RETURN_THRESHOLD = 4
    WARRIOR_SPAWN_TARGET = 2
    FARMER_SPAWN_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.first_attack_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Feed hungry villagers first (eating consumes 1 wheat each).
        hungry = [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD]
        healthy = [c for c in components if c.steps_since_meal < self.VILLAGE_EAT_THRESHOLD]
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_left = wheat - len(hungry)

        # Spawners are chosen from the healthy villagers, preferring farmers
        # so that warriors stay available for combat.
        farmers = [c for c in healthy if c.role == "Farmer"]
        warriors = [c for c in healthy if c.role == "Warrior"]
        pool = farmers + warriors
        assigned = set()

        # 2) Spawn warriors (2 villagers + 12 wheat each) until the target is reached.
        while (self.warriors_spawned < self.WARRIOR_SPAWN_TARGET
               and wheat_left >= self.WARRIOR_COST
               and len([c for c in pool if id(c) not in assigned]) >= 2):
            pair = [c for c in pool if id(c) not in assigned][:2]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                assigned.add(id(c))
            self.warriors_spawned += 1
            wheat_left -= self.WARRIOR_COST

        # 3) Spawn farmers (2 villagers + 10 wheat each) until the target is reached.
        while (self.farmers_spawned < self.FARMER_SPAWN_TARGET
               and wheat_left >= self.FARMER_COST
               and len([c for c in pool if id(c) not in assigned]) >= 2):
            pair = [c for c in pool if id(c) not in assigned][:2]
            for c in pair:
                environment.assign_group(c, "spawn farmer")
                assigned.add(id(c))
            self.farmers_spawned += 1
            wheat_left -= self.FARMER_COST

        # 4) Everyone else: farmers farm, warriors go to the Cave to fight.
        dragon_alive = environment.dragon.hp > 0
        for c in healthy:
            if id(c) in assigned:
                continue
            if c.role == "Farmer":
                environment.assign_group(c, "farm")
            elif dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attacked_any = False
        for c in components:
            # Farmers must stay in the Village; starving or hungry villagers return to eat.
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                # Healthy, fed warriors attack every step to prevent regeneration.
                environment.assign_group(c, "attack")
                attacked_any = True

        if attacked_any and self.first_attack_step is None:
            self.first_attack_step = step