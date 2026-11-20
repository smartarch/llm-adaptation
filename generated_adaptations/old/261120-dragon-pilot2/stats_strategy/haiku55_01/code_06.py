from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors run a short cycle: ~3 attack steps in the Cave, then return to the Village
      to eat immediately and go straight back. This keeps most warriors attacking each step.
    - Farmers eat only when needed (threshold 3) and otherwise farm wheat.
    - Meals are reserved first; the rest of the wheat is used for as many
      "spawn warrior" pairs (2 farmers per 12 wheat) as possible each step.
    - Farmers never enter the Cave.
    """

    WARRIOR_LEAVE_CAVE_AT = 3   # warriors in the Cave return once this many steps have passed
    FARMER_EAT_AT = 3           # farmers eat at this threshold
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals first.
        eaters = []
        for c in warriors:
            # Warriors that are not freshly fed eat right away; fresh ones (0 steps) go back to the Cave.
            if c.steps_since_meal >= 1:
                eaters.append(c)
        for c in farmers:
            if c.steps_since_meal >= self.FARMER_EAT_AT:
                eaters.append(c)

        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        eater_ids = {id(c) for c in eaters}
        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Spawn warriors with as many farmer pairs as the wheat budget allows.
        spawn_ids = set()
        while wheat >= self.WARRIOR_COST and len(idle_farmers) >= 2:
            pair = idle_farmers[:2]
            idle_farmers = idle_farmers[2:]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 3) Fresh warriors head to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 4) Remaining farmers farm wheat.
        for c in idle_farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")