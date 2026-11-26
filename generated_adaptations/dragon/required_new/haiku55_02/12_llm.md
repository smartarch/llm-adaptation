## Diagnosis

The two remaining failures are both "Dragon not killed within 30 steps." Feeding and assignment are correct, so the issue is still damage output. The current win rate is 67%, with an average win at step 25, which means the Dragon is usually killed late. Two things are slowing the kill:

- **The endgame switch comes too late.** Farmers only join the attack once the Dragon is at 15 HP or less. At that point the Dragon has roughly 15 HP left, but farmers need several steps to add up 1 damage each. Switching at 25 HP gives more steps of extra damage.
- **Wheat sits idle when it could fund spawns.** The spawn rule keeps a reserve for next step's meals only. Once wheat is comfortably above that reserve, the code still sends healthy farmers to the farm instead of the cave. When the reserve is covered, extra farmers should attack.

I could not run the simulation, so these values are estimates, not measured results. The main risk is starvation: farmers in the cave stop producing wheat, so the endgame push is only applied when wheat covers the meals due next step.

## Revised strategy

**Village:**
1. Feed by urgency. Villagers with `steps_since_meal >= 3` eat while wheat lasts. Anyone who cannot be fed farms instead.
2. Spawn warriors from pairs of non-hungry farmers while wheat covers the warrior cost plus the meals due next step. Spawning runs through step 26.
3. Healthy warriors attack in the cave.
4. Endgame push: when the Dragon is at 25 HP or less and wheat covers the meals due next step plus a margin of 2, healthy, non-hungry farmers also attack.
5. Everyone else farms.

**Cave:** Unchanged. Villagers attack until they reach 4 steps without a meal or drop to 2 HP or less, then return to the village.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry farmers while the wheat left over
      covers the meals due next step.
    - Healthy warriors attack in the Cave. Once the Dragon is at 25 HP or less
      and wheat is comfortably available, healthy non-hungry farmers attack too.
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
    ENDGAME_DRAGON_HP = 25         # from this point, farmers also attack
    ENDGAME_WHEAT_MARGIN = 2       # extra wheat needed before farmers leave the farm
    MIN_HP_IN_CAVE = 2             # return to village at or below this HP

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
                   and wheat - self.WARRIOR_SPAWN_COST >= needs_next):
                pair = [c for c in spawn_candidates if c not in spawned][:2]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.append(c)
                wheat -= self.WARRIOR_SPAWN_COST

        # 4) Decide who attacks in the endgame, if wheat is comfortable.
        endgame_farmers_ok = endgame and wheat >= needs_next + self.ENDGAME_WHEAT_MARGIN

        # 5) Fight or farm.
        for c in unfed:
            if c in spawned:
                continue
            if c.role == "Warrior" and c.hp >= self.MIN_WARRIOR_HP_FOR_CAVE:
                environment.assign_group(c, "cave")
            elif (endgame_farmers_ok and c.role == "Farmer"
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