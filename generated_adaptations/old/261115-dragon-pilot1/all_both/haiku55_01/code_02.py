import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Villagers:
      - Anyone with steps_since_meal >= 3 eats first (keeps everyone far from the
        6-step starvation limit, and keeps hungry warriors out of the cave).
      - Fed warriors go to the cave and attack the dragon.
      - Warriors that become hungry in the cave return to the village to eat.
      - Farmers stay in the village, farm, or form pairs to spawn new
        warriors (12 wheat) and new farmers (10 wheat), at least two of each.
    """

    HUNGER_THRESHOLD = 3       # eat when this many steps have passed without a meal
    MIN_SPAWNS = 2             # at least this many of each role should be spawned

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat, cave, farmers_free, warriors_hungry = [], [], [], []

        # 1) Decide who must eat (hungry villagers first, most hungry first)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        meals_affordable = max(0, int(wheat))
        for c in hungry:
            if len(eat) < meals_affordable or c.steps_since_meal >= 5:
                eat.append(c)
            else:
                warriors_hungry.append(c) if c.role == "Warrior" else farmers_free.append(c)
        wheat_after_meals = wheat - len(eat)

        # 2) Non-hungry villagers
        for c in components:
            if c in eat or c in warriors_hungry or c in farmers_free:
                continue
            if c.role == "Warrior":
                cave.append(c)              # fed warriors go attack the dragon
            else:
                farmers_free.append(c)      # farmers stay in the village

        # 3) Spawning among free farmers (pairs), warriors first, then farmers
        spawn_warrior, spawn_farmer = [], []
        available = list(farmers_free)
        remaining_wheat = wheat_after_meals

        if (self.spawned_warriors < self.MIN_SPAWNS
                and remaining_wheat >= 12 and len(available) >= 2):
            spawn_warrior = available[:2]
            available = available[2:]
            remaining_wheat -= 12
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and remaining_wheat >= 10 and len(available) >= 2):
            spawn_farmer = available[:2]
            available = available[2:]
            remaining_wheat -= 10
            self.spawned_farmers += 1

        farm = available

        # 4) Issue assignments (every component must be assigned exactly once)
        for c in eat:
            environment.assign_group(c, "eat")
        for c in cave:
            environment.assign_group(c, "cave")
        for c in warriors_hungry:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in farm:
            environment.assign_group(c, "farm")

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.HUNGER_THRESHOLD:
                    # hungry: must go home and eat before it starves
                    environment.assign_group(c, "village")
                else:
                    # fed and healthy: keep the dragon under attack
                    environment.assign_group(c, "attack")
            else:
                # farmers must not stay in the cave
                environment.assign_group(c, "village")