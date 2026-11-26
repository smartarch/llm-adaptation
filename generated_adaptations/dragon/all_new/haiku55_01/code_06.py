from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy-first adaptation:
      - Anyone at steps_since_meal >= 3 eats (village) or retreats to eat (cave).
      - Early on, spawn farmers (cheap, 5 wheat/step payback) until a farmer
        target is reached, to build a wheat engine.
      - Afterwards, spawn warriors (the only real attackers) whenever affordable.
      - Spawn inputs are any two free villagers, preferring farmers.
      - Warriors attack every step in the cave so the Dragon never regenerates.
    """

    EAT_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    EARLY_STEP_LIMIT = 12
    FARMER_TARGET = 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)
        population = n_farmers + n_warriors

        # 1) Feed anyone approaching the starvation limit.
        free = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                free.append(c)

        # Prefer farmers as spawn inputs (they are the least useful attackers).
        free.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
        used = set()

        # 2) Spawning: consume free pairs while wheat allows.
        while True:
            pool = [c for c in free if id(c) not in used]
            if len(pool) < 2:
                break

            reserve = population  # one meal per living villager
            spawn_farmer = (
                step <= self.EARLY_STEP_LIMIT
                and n_farmers < self.FARMER_TARGET
                and wheat - reserve >= self.FARMER_COST
            )
            spawn_warrior = wheat - reserve >= self.WARRIOR_COST

            if spawn_farmer:
                group, cost = "spawn farmer", self.FARMER_COST
                n_farmers += 1
            elif spawn_warrior:
                group, cost = "spawn warrior", self.WARRIOR_COST
                n_warriors += 1
            else:
                break

            for c in pool[:2]:
                environment.assign_group(c, group)
                used.add(id(c))
            wheat -= cost
            population += 1

        # 3) Route the rest: warriors attack, farmers farm.
        for c in free:
            if id(c) in used:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                # Retreat to eat before starvation sets in.
                environment.assign_group(c, "village")
            else:
                # Keep attacking every step so the Dragon never regenerates.
                environment.assign_group(c, "attack")