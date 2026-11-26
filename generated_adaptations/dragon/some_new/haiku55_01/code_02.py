from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: villagers that have not eaten for >= 2 steps go to 'eat'.
        Spawn a warrior (pair of farmers in 'spawn warrior') when wheat allows.
        Healthy warriors go to the 'cave' to attack; farmers keep farming.
      - Cave: villagers that have not eaten for >= 3 steps or are almost dead
        return to the 'village'; all others attack the Dragon.
    The cycle keeps the Dragon under continuous attack (no regeneration)
    while ensuring that nobody reaches the 6-step starvation limit.
    """

    EAT_THRESHOLD_VILLAGE = 2
    RETURN_THRESHOLD_CAVE = 3
    MIN_HP_TO_STAY = 2
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        to_eat = []
        ready = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                to_eat.append(c)
            else:
                ready.append(c)

        # Wheat budget after reserving wheat for this step's meals
        budget = wheat - len(to_eat)

        ready_farmers = [c for c in ready if c.role == "Farmer"]
        ready_warriors = [c for c in ready if c.role == "Warrior"]

        spawn_group = []
        if budget >= self.WARRIOR_SPAWN_COST and len(ready_farmers) >= 2:
            spawn_group = ready_farmers[:2]
            budget -= self.WARRIOR_SPAWN_COST
        spawn_ids = {id(c) for c in spawn_group}

        for c in components:
            if c in to_eat:
                environment.assign_group(c, "eat")
            elif id(c) in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif c.role == "Warrior" and c.hp >= self.MIN_HP_TO_STAY:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if (c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE
                    or c.hp <= 1):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")