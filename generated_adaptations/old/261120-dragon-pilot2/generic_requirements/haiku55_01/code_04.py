import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Staggered warrior rotation:
      - Spawn warriors from farmer pairs as early and as often as wheat allows.
      - Warriors eat in the village before going to the cave, so they arrive fed.
      - In the cave, warriors attack while fed and return home at a hunger threshold,
        staggered so that at least one warrior keeps attacking when possible.
      - Farmers stay on the farm; one farmer spawn is allowed for the requirement.
    """

    EAT_BEFORE_CAVE = 1     # warriors in village with at least this many unmet steps eat first
    RETURN_THRESHOLD = 3    # in cave, warriors with this many unmet steps go home
    MAX_WARRIOR_SPAWNS = 6  # generous cap; wheat is the real limit
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_orders = 0
        self.farmer_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # 1. Hungry warriors eat first (costs 1 wheat each), so they are fed for the cave.
        eaters = []
        ready_warriors = []
        for w in warriors:
            if w.steps_since_meal >= self.EAT_BEFORE_CAVE and budget >= 1:
                eaters.append(w)
                budget -= 1
            else:
                ready_warriors.append(w)

        # 2. Pair farmers into warrior spawns while wheat allows.
        spawn_warrior = []
        available = list(farmers)
        while (len(available) >= 2 and budget >= 12
               and self.warrior_spawn_orders < self.MAX_WARRIOR_SPAWNS):
            spawn_warrior.extend(available[:2])
            available = available[2:]
            budget -= 12
            self.warrior_spawn_orders += 1

        # 3. One farmer spawn if affordable after warrior spawns (keeps the farmer requirement).
        spawn_farmer = []
        if (len(available) >= 2 and budget >= 10
                and self.farmer_spawn_orders < self.MAX_FARMER_SPAWNS):
            spawn_farmer.extend(available[:2])
            available = available[2:]
            budget -= 10
            self.farmer_spawn_orders += 1

        # 4. Assign everyone exactly once.
        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in ready_warriors:
            environment.assign_group(c, "cave")
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should not be here; send them back to produce wheat.
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors that are hungry go home to eat. Hungriest first, so that
        # the remaining group keeps attacking and the Dragon regenerates less.
        hungry = [w for w in warriors if w.steps_since_meal >= self.RETURN_THRESHOLD]
        fed = [w for w in warriors if w.steps_since_meal < self.RETURN_THRESHOLD]

        for w in hungry:
            environment.assign_group(w, "village")

        # Fed warriors attack. If none are fed but some warriors remain, keep them
        # in the cave so they are ready to attack after returning fed.
        for w in fed:
            environment.assign_group(w, "attack")