## Diagnosis

The remaining failures are all `test_no_required_constraints_violated_at_the_end`, and the message is "To win the game, the Dragon must be killed." Feeding and assignment are now correct. The problem is that the Dragon survives within 30 steps in about two-thirds of runs, so the strategy needs more damage sooner.

Three factors limit damage:

- **Spawning stops too early.** The spawn window closes at step 24, and the wheat margin holds back spawns that would still add damage for several steps.
- **Warriors spend about 20% of their time in the village.** A warrior that reaches 4 steps without a meal must walk home and eat. That's necessary for survival, but it removes attackers from the cave during those steps.
- **Wheat is left idle.** Once the margin is covered, extra wheat should go into more warriors.

## Revised strategy

**Village:**
1. **Feed by urgency.** Villagers with `steps_since_meal >= 3` eat when wheat allows. Anyone who can't be fed farms instead, so there are no invalid assignments.
2. **Spawn more aggressively.** The spawn window now runs to step 26. The wheat margin is reduced to zero, but the reserve still covers the meals due in the next step, so no one starves.
3. **Healthy warriors fight.** Warriors with `hp >= 3` go to the cave. Everyone else farms.

**Cave:**
1. Warriors attack until they reach 4 steps without a meal or drop to 2 HP or less, then return to the village. This keeps the 4-step threshold, which leaves a safety margin under the 6-step starvation limit.

The changes target the Dragon's remaining HP through more warriors, spawned sooner, and fewer idle wheat reserves. Two tuning values remain uncertain, so the simulation may need to confirm them:
- A spawn cutoff of 26 is a judgment call. A later spawn gives fewer attack steps but costs little.
- A margin of zero is the riskiest change, because it leaves no slack for the Dragon's attacks on villagers in the cave. The test suite will show whether the starvation checks still pass.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry farmers whenever the wheat left
      over still covers the meals due in the next step. Spawning continues
      until step 26 so new warriors have time to deal damage.
    - Healthy warriors attack in the Cave; everyone else farms.
    - In the Cave, warriors attack until they are hungry (4+ steps without a
      meal) or badly hurt (HP <= 2), then return to the Village.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 26          # late spawns still add some damage
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP
    WHEAT_MARGIN = 0               # reserve only what the next meals need

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        all_villagers = list(environment.warriors) + list(environment.farmers)

        # 1) Feed the most urgent villagers first, as long as wheat allows.
        fed = []
        unfed = []
        for c in sorted(components, key=lambda v: -v.steps_since_meal):
            if c.steps_since_meal >= self.HUNGER_THRESHOLD_VILLAGE and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
                fed.append(c)
            else:
                unfed.append(c)

        # 2) Meals due next step from villagers not fed this step.
        needs_next = sum(1 for v in all_villagers if v.steps_since_meal >= self.HUNGER_SOON)
        needs_next = max(0, needs_next - len(fed))

        # 3) Spawn warriors from pairs of non-hungry farmers while wheat allows.
        spawned = []
        if step <= self.SPAWN_STEP_LIMIT:
            spawn_candidates = [
                c for c in unfed
                if c.role == "Farmer" and c.steps_since_meal < self.HUNGER_THRESHOLD_VILLAGE
            ]
            while (len(spawn_candidates) - len(spawned) >= 2
                   and wheat - self.WARRIOR_SPAWN_COST >= needs_next + self.WHEAT_MARGIN):
                pair = [c for c in spawn_candidates if c not in spawned][:2]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.append(c)
                wheat -= self.WARRIOR_SPAWN_COST

        # 4) Healthy warriors fight; everyone else farms.
        for c in unfed:
            if c in spawned:
                continue
            if c.role == "Warrior" and c.hp >= self.MIN_WARRIOR_HP_FOR_CAVE:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if (c.steps_since_meal >= self.HUNGER_THRESHOLD_CAVE
                    or c.hp <= self.MIN_HP_IN_CAVE):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```