import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Army-first strategy:
      - Spawn warriors from any available farmer pair when wheat allows,
        at most one warrior spawn per step, with a reserve for meals.
      - Keep at least one farmer on the farm for wheat income.
      - One early farmer spawn satisfies the requirement for new farmers.
      - Villagers that are due for food eat in the village first.
      - Fed warriors attack in the cave and return home at RETURN_THRESHOLD steps.
    """

    EAT_IN_VILLAGE_MIN = 3        # villagers in the village eat once this many steps have passed
    RETURN_THRESHOLD = 4          # cave warriors go home at this many unmet steps
    FARM_MIN = 1                  # farmers kept on the farm for wheat income
    MAX_WARRIOR_SPAWNS_PER_STEP = 1
    EARLY_FARMER_STEP = 8
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # 1. Villagers that are due for food eat first (1 wheat each).
        eaters = []
        for c in components:
            if c.steps_since_meal >= self.EAT_IN_VILLAGE_MIN and budget >= 1:
                eaters.append(c)
                budget -= 1
        eaten_ids = set(id(c) for c in eaters)

        # 2. Reserve wheat for villagers who will need food soon.
        reserve = sum(1 for c in components
                      if id(c) not in eaten_ids and c.steps_since_meal >= 2)
        spendable = budget - reserve

        available = [f for f in farmers if id(f) not in eaten_ids]

        # 3. One early farmer spawn to satisfy the requirement.
        spawn_farmer = []
        if (step <= self.EARLY_FARMER_STEP and len(available) >= 2
                and spendable >= 10 and self.farmer_spawn_orders < self.MAX_FARMER_SPAWNS):
            spawn_farmer = available[:2]
            available = available[2:]
            spendable -= 10
            self.farmer_spawn_orders += 1

        # 4. At most one warrior spawn per step, from a farmer pair,
        #    keeping FARM_MIN farmers working if possible.
        spawn_warrior = []
        warrior_spawns = 0
        while (warrior_spawns < self.MAX_WARRIOR_SPAWNS_PER_STEP
               and len(available) >= 2 and spendable >= 12):
            if len(available) - 2 < self.FARM_MIN and len(available) > 2:
                break
            spawn_warrior = available[:2]
            available = available[2:]
            spendable -= 12
            warrior_spawns += 1

        # 5. Assign everyone exactly once.
        spawn_ids = set(id(c) for c in spawn_farmer + spawn_warrior)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")

        for w in warriors:
            if id(w) in eaten_ids or id(w) in spawn_ids:
                continue
            if w.steps_since_meal >= self.EAT_IN_VILLAGE_MIN:
                # No wheat to eat this step: stay and wait, do not walk to the cave hungry.
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should not be here; send them back to produce wheat.
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors near starvation go home; the rest keep attacking.
        for w in warriors:
            if w.steps_since_meal >= self.RETURN_THRESHOLD:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")