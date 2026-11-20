import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Continuous warrior production:
      - Farmer pairs are turned into warriors whenever wheat covers the spawn cost
        plus a reserve for meals; no hard cap on warrior spawns.
      - At least FARM_MIN farmers stay on the farm to keep wheat income alive.
      - One early farmer spawn satisfies the requirement for new farmers.
      - Warriors eat in the village at 3+ unmet steps, attack in the cave,
        and return home at RETURN_THRESHOLD unmet steps.
    """

    EAT_IN_VILLAGE_MIN = 3   # village villagers eat once this many steps have passed
    RETURN_THRESHOLD = 4     # cave warriors go home at this many unmet steps
    FARM_MIN = 2             # farmers kept on the farm for wheat income
    EARLY_FARMER_STEP = 6    # farmer spawn is prioritised before this step
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # 1. Villagers that have gone without a meal eat first (1 wheat each).
        eaters = []
        for c in components:
            if c.steps_since_meal >= self.EAT_IN_VILLAGE_MIN and budget >= 1:
                eaters.append(c)
                budget -= 1
        eaten = set(id(c) for c in eaters)

        # Reserve wheat for villagers who will need food soon.
        reserve = sum(1 for c in components if id(c) not in eaten and c.steps_since_meal >= 2)
        spendable = budget - reserve

        available = [f for f in farmers if id(f) not in eaten]

        # 2. Early farmer spawn to satisfy the requirement and grow the economy.
        spawn_farmer = []
        if (step <= self.EARLY_FARMER_STEP and len(available) >= 2 + self.FARM_MIN
                and spendable >= 10 and self.farmer_spawn_orders < self.MAX_FARMER_SPAWNS):
            spawn_farmer.extend(available[:2])
            available = available[2:]
            spendable -= 10
            self.farmer_spawn_orders += 1

        # 3. Turn farmer pairs into warriors while wheat and farm staffing allow.
        spawn_warrior = []
        while len(available) >= 2 + self.FARM_MIN and spendable >= 12:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            spendable -= 12

        # 4. Assign everyone exactly once.
        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")

        for w in warriors:
            if id(w) in eaten or w in spawn_warrior or w in spawn_farmer:
                continue
            environment.assign_group(w, "cave")

        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should not be here; send them back to produce wheat.
        for c in farmers:
            environment.assign_group(c, "village")

        # Hungriest warriors go home first; the rest keep attacking.
        for w in warriors:
            if w.steps_since_meal >= self.RETURN_THRESHOLD:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")