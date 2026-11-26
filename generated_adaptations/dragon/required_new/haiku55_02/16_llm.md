## Diagnosis

The last change made things worse. The win rate dropped from 67% to 33%, so the "fewer than 12 steps left" trigger is the likely cause. It sent farmers to the cave from step 18 onward, which stripped the farm of wheat income. The margin check then blocked more meals and spawns, and some villagers starved or were eaten.

The earlier failures point to a second problem. When every warrior in the cave reaches the hunger threshold on the same step, they all walk home together. The cave is then empty for a step or more, and the Dragon regenerates 5 HP. Each gap costs about 5 HP and undoes damage from the surrounding steps.

## Revised strategy

**Village:**
1. Revert the endgame trigger to the Dragon's HP only (25 HP or less). The step-based trigger is removed.
2. Keep the feeding, spawning, and wheat-margin logic from the previous version, since it passed the feeding and assignment tests.

**Cave:**
1. Villagers with `hp <= 2` always go home, since they could die to the Dragon's attacks.
2. Villagers with `steps_since_meal >= 4` also go home, to stay under the 6-step starvation limit.
3. If every villager in the cave would leave on the same step, the least hungry one stays to attack. This keeps at least one attacker active each step, so the Dragon never regenerates while a hungry villager is still safe to keep fighting.

I could not run the simulation, so the thresholds are estimates. The step-based endgame trigger was the clearest regression, so I removed it.

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
    - In the Cave, villagers attack until they are hungry (4+ steps without a
      meal) or badly hurt (HP <= 2), then return to the Village. The least
      hungry villager stays to attack if everyone would otherwise leave at once,
      so the Dragon never gets a free regeneration step.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 4      # return from the cave to eat at this point
    SPAWN_STEP_LIMIT = 26          # late spawns still add some damage
    WARRIOR_SPAWN_COST = 12
    MIN_WARRIOR_HP_FOR_CAVE = 3
    MIN_FARMER_HP_FOR_ENDGAME = 3
    ENDGAME_DRAGON_HP = 25         # farmers attack once the Dragon is at or below this
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

        # Keep at least one attacker in the cave so the Dragon never regenerates
        # on a step when nobody attacks. Keep the least urgent villager that is
        # not critically hurt or starving.
        if not staying and leaving:
            safe_to_keep = [
                c for c in leaving
                if c.hp > self.MIN_HP_IN_CAVE
                and c.steps_since_meal < self.HUNGER_THRESHOLD_CAVE + 1
            ]
            if safe_to_keep:
                keep = min(safe_to_keep, key=lambda c: c.steps_since_meal)
                leaving.remove(keep)
                staying.append(keep)

        for c in leaving:
            environment.assign_group(c, "village")
        for c in staying:
            environment.assign_group(c, "attack")
```