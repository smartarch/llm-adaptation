from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - In the Village, villagers eat once they have gone 2 steps unfed (most hungry first,
        limited by wheat).
      - Spawning: one Farmer is spawned first (required), and after that Warriors are
        spawned whenever wheat allows (they deal 3 damage per attack versus 1 for Farmers).
        Two Warriors are required, so the first Warrior spawns are prioritized.
      - Fed Warriors go to the Cave and attack every step they can.
      - In the Cave, Warriors attack while they have gone fewer than 3 steps unfed; then
        they return to the Village (one step) and eat on arrival, staying under the
        6-step starvation limit.
    """

    EAT_THRESHOLD_VILLAGE = 2
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LAST_SPAWN_STEP = 25
    MIN_FARMER_SPAWNS = 1
    MIN_WARRIOR_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self.warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # Most hungry villagers first.
        ordered = sorted(components, key=lambda c: c.steps_since_meal, reverse=True)

        # Feed hungry villagers, limited by available wheat.
        hungry = [c for c in ordered if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        eat_list = hungry[:wheat]
        eat_ids = {id(c) for c in eat_list}
        budget = wheat - len(eat_list)

        # Farmers not eating this step are the spawn candidates.
        farmers = [c for c in ordered if id(c) not in eat_ids and c.role == "Farmer"]

        spawn_group = None  # (group name, members)
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            can_farmer = budget >= self.FARMER_SPAWN_COST
            can_warrior = budget >= self.WARRIOR_SPAWN_COST
            need_farmer = self.farmers_spawned < self.MIN_FARMER_SPAWNS
            need_warrior = self.warriors_spawned < self.MIN_WARRIOR_SPAWNS

            if need_farmer and not need_warrior and can_farmer:
                # Only the required Farmer is still missing.
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1
            elif can_warrior:
                # Warriors are the main damage source; spawn them whenever affordable.
                spawn_group = ("spawn warrior", farmers[:2])
                budget -= self.WARRIOR_SPAWN_COST
                self.warriors_spawned += 1
            elif can_farmer:
                # Warrior unaffordable: a Farmer adds wheat and satisfies the requirement.
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1

        spawn_ids = {id(c) for c in spawn_group[1]} if spawn_group else set()

        # Assign every villager to exactly one group.
        for c in ordered:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, spawn_group[0])
            elif c.role == "Farmer":
                environment.assign_group(c, "farm")
            elif c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                # Unfed warrior that could not be fed this step: stay and eat later.
                environment.assign_group(c, "farm")
            else:
                # Fed warrior: go attack the Dragon.
                environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")