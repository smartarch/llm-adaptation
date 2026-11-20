from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - In the Village, villagers eat once they have gone 2 steps unfed (most hungry first,
        limited by wheat).
      - Spawning: one Farmer first (required), then Warriors whenever wheat allows after
        reserving wheat for Warriors that will be hungry next step.
      - Fed Warriors leave for the Cave in a staggered way (at most one fewer than the
        number of Warriors per step, longest-unfed first) so the Dragon is attacked
        without long breaks.
      - In the Cave, Warriors attack while they have gone fewer than 3 unfed steps, then
        return to the Village (one step) and eat on arrival.
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

        # Warriors not fed this step will need wheat next step; keep it reserved.
        reserve = sum(
            1 for c in ordered
            if id(c) not in eat_ids and c.role == "Warrior"
            and c.steps_since_meal + 1 >= self.EAT_THRESHOLD_VILLAGE
        )

        # Farmers not eating this step are the spawn candidates.
        farmers = [c for c in ordered if id(c) not in eat_ids and c.role == "Farmer"]

        spawn_group = None  # (group name, members)
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            can_farmer = budget - reserve >= self.FARMER_SPAWN_COST
            can_warrior = budget - reserve >= self.WARRIOR_SPAWN_COST
            need_farmer = self.farmers_spawned < self.MIN_FARMER_SPAWNS
            need_warrior = self.warriors_spawned < self.MIN_WARRIOR_SPAWNS

            if need_farmer and not need_warrior and can_farmer:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1
            elif can_warrior:
                spawn_group = ("spawn warrior", farmers[:2])
                budget -= self.WARRIOR_SPAWN_COST
                self.warriors_spawned += 1
            elif can_farmer:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1

        spawn_ids = {id(c) for c in spawn_group[1]} if spawn_group else set()

        # Fed warriors (not eating, not hungry) are candidates for the Cave.
        fed_warriors = [
            c for c in ordered
            if id(c) not in eat_ids and id(c) not in spawn_ids
            and c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE
        ]
        total_warriors = sum(1 for c in components if c.role == "Warrior")

        # Stagger: keep at least one Warrior back so the Dragon keeps getting attacked.
        max_to_cave = max(1, total_warriors - 1) if total_warriors > 0 else 0
        # Longest-unfed warriors leave first.
        fed_warriors.sort(key=lambda c: c.steps_since_meal, reverse=True)
        cave_ids = {id(c) for c in fed_warriors[:max_to_cave]}

        # Assign every villager to exactly one group.
        for c in ordered:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, spawn_group[0])
            elif c.role == "Farmer":
                environment.assign_group(c, "farm")
            elif cid in cave_ids:
                environment.assign_group(c, "cave")
            else:
                # Warrior held back this step (hungry, or staggered): stay and farm/eat later.
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")