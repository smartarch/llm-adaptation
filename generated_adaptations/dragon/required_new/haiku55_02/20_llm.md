## Diagnosis

The starvation and assignment tests pass now, so the cave timing is correct. The remaining failures are all "Dragon not killed within 30 steps," so the problem is damage output again.

I re-read the rules and found a gap in my spawning logic. The spawn group accepts any two villagers, not only farmers. My code only ever spawned from farmers, so a warrior resting in the village could never contribute to a spawn. Two changes address this:

- **Spawn from any non-hungry villager.** Farmers are used first, since they produce the least per step. If too few farmers are available, healthy non-hungry warriors resting in the village can form the pair. A spawned warrior is worth far more damage than the one step of attacking that the pair gives up.
- **Spawn earlier in the fight.** The spawn cutoff moves from step 26 to step 28. A warrior spawned at step 28 can still attack in the cave for a step or two before the limit.

The cave logic is unchanged, so the starvation checks should still pass. I could not run the simulation, so these effects are estimates. If the win rate does not improve, the next thing to test is the cave rotation, since it sets how many attacks each warrior gets per cycle.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Feed villagers in order of urgency. Anyone with 3+ steps without a meal
      eats in the village if wheat allows; otherwise they farm.
    - Spawn warriors from pairs of non-hungry villagers while the wheat left
      over covers the meals due next step. Farmers are used first; healthy
      warriors resting in the village fill in when farmers run out.
    - Healthy warriors attack in the Cave. Once the Dragon is at 25 HP or less,
      healthy non-hungry farmers also attack, provided wheat still covers the
      meals due next step.
    - In the Cave, villagers attack until they have gone 3 steps without a meal
      or are badly hurt (HP <= 2), then return to the Village. The least hungry
      villager stays to attack if everyone would otherwise leave at once.
    """

    HUNGER_THRESHOLD_VILLAGE = 3   # eat in the village at this point
    HUNGER_SOON = 2                # will need a meal next step
    HUNGER_THRESHOLD_CAVE = 3      # return from the cave to eat at this point
    KEEP_ATTACKER_MAX_HUNGER = 1   # only keep an attacker this fresh
    SPAWN_STEP_LIMIT = 28
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

        # 3) Spawn warriors from pairs of non-hungry villagers while wheat allows.
        #    Farmers are preferred because they contribute less when attacking.
        spawned = []
        if step <= self.SPAWN_STEP_LIMIT:
            spawn_candidates = sorted(
                [c for c in unfed if c.steps_since_meal < self.HUNGER_THRESHOLD_VILLAGE],
                key=lambda c: (c.role != "Farmer", -c.hp),
            )
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
        # Dragon does not get a free regeneration step.
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