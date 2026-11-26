from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: villagers at or above this hunger are sent to eat
    EAT_THRESHOLD = 2
    # Cave: warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village: warriors this fed (or less) are dispatched to the cave
    DISPATCH_MAX_HUNGER = 1
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave: warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    # Wheat kept back for next step's meals
    WHEAT_RESERVE = 2
    WARRIOR_SPAWN_COST = 12
    # Spawn only early enough that new warriors can still attack
    SPAWN_STEP_LIMIT = 12
    # Keep at least this many farmers on the farm
    MIN_FARMERS_ON_FARM = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # 1) Feed the most hungry villagers first, limited by available wheat
        needy = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        eaters = needy[:wheat]
        eater_ids = set(id(c) for c in eaters)
        remaining_wheat = wheat - len(eaters)

        rest = [c for c in components if id(c) not in eater_ids]

        # 2) Send every fed, healthy warrior to the cave
        cave_ids = set(
            id(c) for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        )

        # 3) Spawn warriors from idle farmers while wheat allows
        idle_farmers = [c for c in rest if c.role == "Farmer"]
        spawn_ids = set()
        spare_farmers = len(idle_farmers) - self.MIN_FARMERS_ON_FARM
        if (
            step < self.SPAWN_STEP_LIMIT
            and spare_farmers >= 2
            and remaining_wheat >= self.WARRIOR_SPAWN_COST + self.WHEAT_RESERVE
        ):
            for c in idle_farmers[:2]:
                spawn_ids.add(id(c))

        # 4) Assign every component exactly once
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in cave_ids:
                environment.assign_group(c, "cave")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hungry = c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD
            if c.role == "Warrior":
                weak = c.hp <= self.WARRIOR_RETREAT_HP
            else:
                # Farmers should not be in the cave; send any back to farm
                weak = True

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")