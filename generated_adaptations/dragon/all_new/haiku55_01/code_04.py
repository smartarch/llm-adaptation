from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Revised adaptation:
      - Farmers stay on the farm (wheat production) or help spawn; they do not
        go to the cave, since their damage (1) is too small to justify it.
      - Warriors are the attackers: they go to the cave and attack every step,
        which prevents the Dragon from regenerating.
      - Warriors are spawned whenever wheat covers the cost plus a meal reserve
        for everyone alive and two farmers are free. Early on, farmers are also
        spawned while the population is small, to grow wheat income.
      - Anyone with steps_since_meal >= 3 eats (in the Village) or retreats to
        the Village to eat (from the Cave), keeping well below the 6-step limit.
    """

    EAT_THRESHOLD = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    FARMER_SPAWN_STEP_LIMIT = 12
    SMALL_POPULATION = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        population = len(environment.warriors) + len(environment.farmers)
        reserve = population  # one meal per living villager

        eating = []
        free_farmers = []
        free_warriors = []

        # 1) Feed anyone approaching the starvation limit.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and wheat >= 1:
                environment.assign_group(c, "eat")
                eating.append(c)
                wheat -= 1
            elif c.role == "Farmer":
                free_farmers.append(c)
            else:
                free_warriors.append(c)

        # 2) Spawning. Use two free farmers as inputs.
        spawn_inputs = []
        if len(free_farmers) >= 2 and wheat - reserve >= self.WARRIOR_COST:
            spawn_inputs = free_farmers[:2]
            for c in spawn_inputs:
                environment.assign_group(c, "spawn warrior")
            wheat -= self.WARRIOR_COST
        elif (len(free_farmers) >= 2
              and step <= self.FARMER_SPAWN_STEP_LIMIT
              and population < self.SMALL_POPULATION
              and wheat - reserve >= self.FARMER_COST):
            spawn_inputs = free_farmers[:2]
            for c in spawn_inputs:
                environment.assign_group(c, "spawn farmer")
            wheat -= self.FARMER_COST

        used = set(id(c) for c in spawn_inputs)

        # 3) Route the rest: warriors attack, farmers farm.
        for c in free_warriors:
            environment.assign_group(c, "cave")

        for c in free_farmers:
            if id(c) in used:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                # Retreat to eat before starvation sets in.
                environment.assign_group(c, "village")
            else:
                # Keep attacking every step so the Dragon never regenerates.
                environment.assign_group(c, "attack")