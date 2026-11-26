## Diagnosis

The failures are all in the cave. Villagers reached 4 steps without a meal while still in the cave, so the starvation check fired before they reached the village.

The cause is the "keep one attacker" rule I added last time. It kept a hungry villager in the cave whenever everyone else was also due to leave, and it allowed a villager at 4 steps to stay. A villager who has reached 4 steps cannot afford another step in the cave, because walking to the village takes one step and eating happens on arrival.

## Fix

- **Leave the cave earlier.** Villagers now return to the village at 3 steps without a meal, not 4. That leaves two steps of margin for the walk and the meal.
- **Restrict the exception.** The keep-one rule now applies only to villagers with `steps_since_meal <= 1`, so the kept attacker can't reach the starvation limit before it leaves.
- **Village logic unchanged.** Feeding, spawning, and the endgame farmer rule stay as before, since the village tests passed.

The "to win" failures are a separate issue. The Dragon still survives in some runs. Shortening the cave stay reduces attack time, so the win rate may drop further. I could not run the simulation to measure this. If the win rate stays low, the next thing to try is spawning warriors earlier or delaying the first cave trip, rather than adding more rules to the cave logic.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry farmers while the wheat left over
      covers the meals due next step.
    - Healthy warriors attack in the Cave. Once the Dragon is at 25 HP or less,
      healthy non-hungry farmers also attack, provided wheat still covers the
      meals due next step.
    - In the Cave, villagers attack until they have gone 3 steps without a meal
      or are badly hurt (HP <= 2), then return to the Village. This leaves two
      steps of margin before the 6-step starvation limit.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 3      # return from the cave to eat at this point
    KEEP_ATTACKER_MAX_HUNGER = 1   # only keep an attacker this fresh
    SPAWN_STEP_LIMIT = 26
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_FARMER_HP_FOR_ENDGAME = 3
    ENDGAME_DRAGON_HP = 25         # farmers attack once the Dragon is at or below this
    ENDGAME_WHEAT_MARGIN = 2
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

        # 4) Decide whether farmers may leave the farm to attack.
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
        # Villagers that must leave now.
        leaving = [
            c for c in components
            if c.steps_since_meal >= self.HUNGER_THRESHOLD_CAVE
            or c.hp <= self.MIN_HP_IN_CAVE
        ]
        staying = [c for c in components if c not in leaving]

        # Keep one fresh attacker if everyone would otherwise leave, so the
        # Dragon does not get a free regeneration step. Only villagers that are
        # not hungry and not badly hurt qualify.
        if not staying and leaving:
            candidates = [
                c for c in leaving
                if c.hp > self.MIN_HP_IN_CAVE
                and c.steps_since_meal <= self.KEEP_ATTACKER_MAX_HUNGER
            ]
            if candidates:
                keep = min(candidates, key=lambda c: c.steps_since_meal)
                leaving.remove(keep)
                staying.append(keep)

        for c in leaving:
            environment.assign_group(c, "village")
        for c in staying:
            environment.assign_group(c, "attack")
```