from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers at or above this hunger are sent to eat in the village
    EAT_THRESHOLD = 2
    # Cave warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village warriors at or below this hunger are dispatched to the cave
    DISPATCH_MAX_HUNGER = 1
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    WARRIOR_SPAWN_COST = 12
    # Keep at least this many farmers working the farm for wheat income
    MIN_FARMERS_ON_FARM = 1

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

        # 2) Send every fresh, healthy warrior to the cave
        cave_list = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        cave_ids = set(id(c) for c in cave_list)

        # 3) Spawn from the remaining villagers, farmers first.
        #    Reserve wheat for next step's meals: villagers that will need food soon.
        upcoming_meals = sum(
            1 for c in components
            if c.steps_since_meal + 1 >= self.EAT_THRESHOLD
        )
        reserve = max(upcoming_meals - len(eaters), 0)
        affordable = (remaining_wheat - reserve) // self.WARRIOR_SPAWN_COST

        spare = [c for c in rest if id(c) not in cave_ids]
        spare.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
        spare_farmers = [c for c in spare if c.role == "Farmer"]

        # Keep the minimum farmers working, then spawn in pairs
        pool = len(spare) - self.MIN_FARMERS_ON_FARM
        spawns = min(max(affordable, 0), max(pool, 0) // 2)

        spawn_ids = set(id(c) for c in spare[: 2 * spawns])

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
                # Farmers should not be in the cave; send any back to the farm
                weak = True

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")