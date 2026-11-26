from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: eat when this many steps have passed without a meal
    VILLAGE_EAT_THRESHOLD = 2
    # Cave: go back to the village when hungry this many steps
    CAVE_RETURN_THRESHOLD = 4
    # Minimum HP for a warrior to be sent to the cave
    WARRIOR_MIN_HP = 3
    # Farmers at or below this HP retreat from the cave
    FARMER_RETREAT_HP = 2
    # Spawning is only worthwhile early in the 30-step game
    SPAWN_STEP_LIMIT = 20
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # Index attributes by component for lookup (attributes are read-only snapshots)
        to_eat = []
        candidates_cave = []
        idle = []

        for c in components:
            hungry = c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD
            if hungry:
                to_eat.append(c)
            elif c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp >= self.WARRIOR_MIN_HP:
                candidates_cave.append(c)
            else:
                idle.append(c)

        # Wheat reserved for this step's meals
        reserved = len(to_eat)
        available = wheat - reserved

        # Decide spawning: two idle farmers in "spawn warrior" per warrior spawn
        spawn = []
        if step < self.SPAWN_STEP_LIMIT and available >= self.WARRIOR_SPAWN_COST:
            idle_farmers = [c for c in idle if c.role == "Farmer"]
            if len(idle_farmers) >= 2:
                spawn = idle_farmers[:2]

        spawn_ids = set(id(c) for c in spawn)
        cave_ids = set(id(c) for c in candidates_cave)

        # Assign everyone exactly once
        for c in components:
            if any(c is e for e in to_eat):
                environment.assign_group(c, "eat")
            elif id(c) in cave_ids:
                environment.assign_group(c, "cave")
            elif id(c) in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hungry = c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD
            weak_farmer = c.role == "Farmer" and c.hp <= self.FARMER_RETREAT_HP
            weak_warrior = c.role == "Warrior" and c.hp <= 1

            if hungry or weak_farmer or weak_warrior:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")