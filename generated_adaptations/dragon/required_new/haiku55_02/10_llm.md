## Diagnosis

The remaining failures are all "Dragon not killed within 30 steps," so feeding and assignment are now correct. Damage output is the bottleneck. Three things limit it:

- **Only warriors attack.** Farmers deal 1 damage per attack, but the strategy keeps them all on the farm even late in the fight, when every point of damage matters.
- **Spawning starts late.** The spawn loop only begins once a pair of farmers is non-hungry and the wheat reserve is met. Warriors spawned in the first few steps contribute the most total damage.
- **The endgame is passive.** When the Dragon is nearly dead, the strategy keeps the same split between farming and fighting. Farmers could finish it.

## Revised strategy

**Village:**
1. **Feed by urgency.** Villagers with `steps_since_meal >= 3` eat when wheat allows. Anyone who can't be fed farms, so there are no invalid assignments.
2. **Spawn from the start.** Spawning runs from step 1 through step 26. Pairs of non-hungry farmers are used while wheat covers the warrior cost plus the meals due next step.
3. **Endgame push.** Once the Dragon has 15 HP or less, healthy, fed farmers also go to the cave. Each adds 1 damage per step, and the Dragon is near death, so the wheat cost of skipping farming is small.
4. **Healthy warriors fight.** Warriors with `hp >= 3` go to the cave. Everyone else farms.

**Cave:**
1. Warriors attack until they reach 4 steps without a meal or drop to 2 HP or less, then return to the village. This keeps a safety margin under the 6-step starvation limit.
2. Farmers in the cave follow the same rule, so the endgame push cannot cause starvation.

I could not run the simulation myself, so these changes are untested. The endgame threshold of 15 HP and the spawn cutoff of 26 are estimates. If the win rate stays low, the next thing to check is whether the Dragon regeneration is wiping out damage during the steps when warriors are walking to eat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry farmers from the start, as long
      as the wheat left over covers the meals due in the next step.
    - Healthy warriors attack in the Cave. When the Dragon is nearly dead,
      healthy fed farmers also join the attack to finish it faster.
    - In the Cave, villagers attack until they are hungry (4+ steps without a
      meal) or badly hurt (HP <= 2), then return to the Village.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 26          # late spawns still add some damage
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_FARMER_HP_FOR_ENDGAME = 3
    ENDGAME_DRAGON_HP = 15         # below this, farmers also attack
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP
    WHEAT_MARGIN = 0               # reserve only what the next meals need

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        all_villagers = list(environment.warriors) + list(environment.farmers)
        endgame = environment.dragon.hp <= self.ENDGAME_DRAGON_HP

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

        # 4) Fight or farm.
        for c in unfed:
            if c in spawned:
                continue
            if c.role == "Warrior" and c.hp >= self.MIN_WARRIOR_HP_FOR_CAVE:
                environment.assign_group(c, "cave")
            elif (endgame and c.role == "Farmer"
                  and c.hp >= self.MIN_FARMER_HP_FOR_ENDGAME
                  and c.steps_since_meal < self.HUNGER_THRESHOLD_VILLAGE):
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