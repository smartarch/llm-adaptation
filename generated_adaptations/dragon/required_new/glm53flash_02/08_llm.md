**Analysis:** we win only when the assault is strong and sustained. The bottlenecks are (a) too few warriors when the assault starts, and (b) hunger round-trips halving our damage. Changes:

1. **Stronger economy:** spawn an extra farmer pair very early (more wheat → more warriors), and keep spawning warrior pairs during the assault whenever wheat allows, replacing losses from the Dragon's counterattacks.
2. **Earlier, committed assault:** start at step ≥ 10 (or ≥ 5 warriors) and keep all warriors attacking; warriors leave the Cave only when hungry (≥ 3) — except when the Dragon is nearly dead, in which case everyone keeps attacking even at hunger 4–5 (starving starts only at 6, so we can squeeze out extra attacks to finish it).
3. **Endgame all-in:** at step ≥ 24, all healthy villagers go to the Cave; farmers eat only if wheat is plentiful, otherwise everyone commits.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 4          # eat in village when this hungry
    LEAVE_CAVE_AT = 3   # leave cave when this hungry (arrive home at 4, eat)
    WARRIOR_CAP = 16

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)
        dragon_hp = environment.dragon.hp

        assault = total_warriors >= 5 or step >= 10
        emergency = step >= 24

        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # ---- spawn planning ----
        w_pairs = 0
        f_pairs = 0
        if not emergency:
            reserve = hungry_count + 10  # food buffer
            budget = wheat - reserve
            if step < 6 and total_villagers < 9:
                f_pairs = max(0, min(1, (budget - 14) // 10))
                budget -= f_pairs * 10
            if step < 20 and total_warriors < self.WARRIOR_CAP:
                w_pairs = max(0, budget // 12)

        w_left = w_pairs * 2
        f_left = f_pairs * 2
        hungry_left = hungry_count

        for c in components:
            # 1) eating has top priority (except all-in endgame for warriors)
            must_eat = c.steps_since_meal >= self.EAT_AT and wheat > 0
            if emergency and c.role == "Warrior" and c.steps_since_meal < 5:
                must_eat = False
            if must_eat:
                environment.assign_group(c, "eat")
                wheat -= 1
                hungry_left -= 1
                continue

            # 2) spawn duties (complete pairs only)
            if w_left >= 2 and not emergency:
                environment.assign_group(c, "spawn warrior")
                w_left -= 1
                wheat -= 6
                continue
            if f_left >= 2 and not emergency:
                environment.assign_group(c, "spawn farmer")
                f_left -= 1
                wheat -= 5
                continue

            # 3) warriors
            if c.role == "Warrior":
                environment.assign_group(c, "cave" if (assault or emergency) else "farm")
                continue

            # 4) farmers: farm or join the final push
            environment.assign_group(c, "cave" if emergency else "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        attackers = [c for c in components if c.steps_since_meal < 6]
        finisher = dragon_hp <= 3 * max(1, len(attackers))

        for c in components:
            if c.steps_since_meal >= 6:
                # starving: useless in the cave, go home to eat
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.LEAVE_CAVE_AT and not finisher:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```