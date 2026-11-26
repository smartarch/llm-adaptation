## Diagnosis

The 18 failures break down into three problems:

1. **Required test (`no_required_constraints_violated_at_the_end`) and win rate 0%:** The strategy never killed the Dragon. Its main flaw was sending farmers to the cave once wheat reached 15. Farmers deal only 1 damage, so this diverted food production without adding meaningful damage. The strategy also spawned at most one warrior early and never built enough attackers.
2. **Optional "farmers should stay in the Village" hints:** Farmers were sent to the cave, which violates the hint. Farmers should keep producing wheat, which pays for food and spawning.
3. **Optional spawn hints (step 11–20, fewer than 5 villagers):** The strategy only spawned warriors, and only up to step 10. It never spawned farmers, and it never used wheat that was clearly available.

## Revised strategy

- **Farmers stay on the farm** (or in the spawn group). They are the wheat engine, and they deal too little damage to justify the cave.
- **Warriors are the only attackers.** They go to the cave and attack every step, which prevents the Dragon's 5 HP/step regeneration.
- **Spawning:**
  - Spawn a **warrior** whenever wheat covers the warrior cost (12) plus a reserve of one meal per living villager, and two farmers are free.
  - Otherwise, while the population is below 5 and early in the fight, spawn a **farmer** (cost 10 plus reserve) to grow wheat income.
- **Feeding:** Any villager with `steps_since_meal >= 3` eats when in the Village, or retreats to the Village from the Cave. The margin keeps everyone well below the 6-step starvation limit, even with travel time.
- **Cave:** Warriors attack every step unless they need to retreat to eat.

The main tradeoff is that spawning warriors costs farm output for a step, so the spawn decision uses the reserve check to avoid starving the population.

```py
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
```