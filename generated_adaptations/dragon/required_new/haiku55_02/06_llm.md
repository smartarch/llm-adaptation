## Diagnosis

The new failures come from wheat accounting in the village:

- **Meals were assigned without checking wheat.** The framework rejects an `eat` assignment when there isn't enough wheat, so the villager was left unassigned (`test_no_invalid_assignments`, `test_all_assigned`).
- **Spawning ignored upcoming meal needs.** Spawning drained wheat down to zero, so the villagers who needed to eat in the next step could not be fed (`test_no_required_constraints_violated`).
- **Hungry farmers could be spawned.** A farmer who was already close to starving could be used in a spawn pair, which delayed the meal they needed.

## Revised strategy

**Village:**
1. **Feed by urgency.** Villagers are sorted by `steps_since_meal`, most urgent first. Each one with `steps_since_meal >= 3` eats if wheat is available. A hungry villager who cannot be fed is sent to "farm" instead of "eat", so no invalid assignment occurs. Starvation is then unavoidable for that villager, but this only happens when wheat is truly exhausted.
2. **Reserve wheat for the next step.** Before spawning, the code counts every villager (in both locations) who will need a meal soon (`steps_since_meal >= 2`), excluding those fed this step. Spawning only happens if the remaining wheat still covers those meals plus a one-wheat margin.
3. **Spawn only from fed farmers.** Spawn pairs come from farmers with `steps_since_meal < 3`, so a near-starving farmer is never used for spawning.
4. **Assign the rest.** Healthy warriors (`hp >= 3`) go to "cave", and everyone else goes to "farm".

**Cave:** Unchanged from the previous version. Warriors attack, and those with `steps_since_meal >= 4` or `hp <= 2` return to the village.

The changes keep every villager assigned exactly once and keep wheat above the meal demand, which addresses the starvation and assignment failures. Spawning still happens early and as often as the reserve allows, which keeps the damage output high for a faster kill.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm (never an
      invalid "eat" assignment).
    - Spawn warriors from pairs of fed farmers, but only while the wheat left
      over still covers the meals that villagers will need in the next step.
    - Healthy warriors attack in the Cave; everyone else farms.
    - In the Cave, warriors attack until they are hungry (4+ steps) or badly
      hurt (HP <= 2), then return to the Village.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 24          # warriors spawned later barely contribute
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP
    WHEAT_MARGIN = 1               # extra wheat kept beyond the next meals

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

        # 2) Estimate meals needed next step from villagers not fed this step.
        #    Villagers fed now reset their clock, so they are excluded.
        needs_next = sum(1 for v in all_villagers if v.steps_since_meal >= self.HUNGER_SOON)
        needs_next = max(0, needs_next - len(fed))

        # 3) Spawn warriors from pairs of farmers that are not hungry.
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

        # 4) Everyone else: healthy warriors fight, the rest farm.
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