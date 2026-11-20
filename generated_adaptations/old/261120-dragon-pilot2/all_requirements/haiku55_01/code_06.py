import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: feed villagers that have gone this many steps without food.
    VILLAGE_EAT_THRESHOLD = 3
    # Cave: warriors return to the Village once they reach this many steps without food.
    CAVE_RETURN_THRESHOLD = 4
    MAX_WARRIORS_SPAWNED = 8   # cap on new warriors (they are the damage dealers)
    MAX_FARMERS_SPAWNED = 1    # at least one new farmer is required
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.first_attack_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat_left = environment.farm.wheat
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        # 1) Feeding has priority. Feed the most-starved villagers first,
        #    as far as the available wheat allows (each meal costs 1 wheat).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat_left >= 1:
                assign(c, "eat")
                wheat_left -= 1
        # Hungry villagers who could not be fed stay in the Village.
        for c in hungry:
            if id(c) not in assigned:
                assign(c, "farm")

        # 2) Spawning. Spawners must be unassigned villagers.
        #    Farmers are preferred as spawners so warriors keep fighting.
        candidates = [c for c in components if id(c) not in assigned]
        farmers = [c for c in candidates if c.role == "Farmer"]
        warriors = [c for c in candidates if c.role == "Warrior"]
        pool = farmers + warriors

        def take_pair():
            free = [c for c in pool if id(c) not in assigned]
            return free[:2] if len(free) >= 2 else None

        # Warriors first: keep spawning while wheat and spawners allow.
        while self.warriors_spawned < self.MAX_WARRIORS_SPAWNED and wheat_left >= self.WARRIOR_COST:
            pair = take_pair()
            if pair is None:
                break
            for c in pair:
                assign(c, "spawn warrior")
            self.warriors_spawned += 1
            wheat_left -= self.WARRIOR_COST

        # Then the required farmer spawn, if wheat is still available.
        while self.farmers_spawned < self.MAX_FARMERS_SPAWNED and wheat_left >= self.FARMER_COST:
            pair = take_pair()
            if pair is None:
                break
            for c in pair:
                assign(c, "spawn farmer")
            self.farmers_spawned += 1
            wheat_left -= self.FARMER_COST

        # 3) Everyone still unassigned.
        #    Fed warriors go to the Cave while the Dragon is alive; farmers farm.
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and dragon_alive and c.steps_since_meal < self.VILLAGE_EAT_THRESHOLD:
                assign(c, "cave")
            else:
                assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attacked_any = False
        for c in components:
            # Farmers must not fight; warriors that have gone too long without food return to eat.
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
                attacked_any = True

        if attacked_any and self.first_attack_step is None:
            self.first_attack_step = step