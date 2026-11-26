**Analysis:** we're plateaued at 33%. The big remaining lever is the hunger cycle: warriors currently leave the Cave at hunger 3, meaning only 3 attack steps per ~7-step cycle. Since starving (HP loss / weakness) only begins after 6 steps without food, the safe optimum is: attack while hunger ≤ 4, then leave (arrive at hunger 5), eat, return. That's a 4/7 ≈ 57% attack duty cycle instead of 3/7. Changes:

1. **LEAVE_CAVE_AT = 4, EAT_AT = 5:** villagers in the Village eat at hunger 5 (still safe — starvation starts at 6), Cave villagers recall at hunger 4, arriving at 5 and eating the same step.
2. **Bigger early economy:** spawn up to 2 farmer pairs in the first few steps (more wheat = more warrior pairs later).
3. **Continuous warrior production:** spawn warrior pairs every step (up to 4 pairs) whenever the budget allows, even during the assault, replacing Dragon-killed warriors.
4. **Finisher mode:** if the Dragon's remaining HP is low, warriors stay and attack even at hunger 4 (one extra attack; they can still safely leave next step since eating at 5 is safe) — but never risk hunger 5 in the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 5          # eat in village when this hungry (starving starts at 6)
    LEAVE_CAVE_AT = 4   # leave cave at 4 -> arrive at 5 -> eat -> safe
    WARRIOR_CAP = 18

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)
        dragon_hp = environment.dragon.hp

        assault = total_warriors >= 4 or step >= 10
        late = step >= 20
        # finisher: dragon nearly dead, squeeze extra attacks
        finisher = assault and dragon_hp <= 4 * max(1, total_warriors)

        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # ---- spawn planning (with food reserve) ----
        reserve = hungry_count + 4
        budget = max(0, wheat - reserve)
        f_pairs = 0
        w_pairs = 0
        if step < 5 and total_villagers < 10:
            f_pairs = max(0, min(2, (budget - 20) // 10))
            budget -= f_pairs * 10
        if total_warriors < self.WARRIOR_CAP:
            w_pairs = max(0, min(4, budget // 12))
            budget -= w_pairs * 12

        w_left = w_pairs * 2
        f_left = f_pairs * 2

        for c in components:
            # 1) eating has top priority, always
            if c.steps_since_meal >= self.EAT_AT and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue

            # 2) spawn duties (complete pairs only)
            if w_left >= 2:
                environment.assign_group(c, "spawn warrior")
                w_left -= 1
                wheat -= 6
                continue
            if f_left >= 2:
                environment.assign_group(c, "spawn farmer")
                f_left -= 1
                wheat -= 5
                continue

            # 3) warriors: attack during assault
            if c.role == "Warrior":
                environment.assign_group(c, "cave" if (assault or late) else "farm")
                continue

            # 4) farmers: mostly farm; surplus joins the assault when rich
            if late and c.steps_since_meal <= 2 and wheat >= 8:
                environment.assign_group(c, "cave")
            elif assault and total_warriors >= 6 and wheat >= 40 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        attackers = [c for c in components if c.steps_since_meal < self.LEAVE_CAVE_AT]
        finisher = dragon_hp <= 3 * max(1, len(attackers))

        for c in components:
            # absolute safety: never let a villager reach hunger 6
            if c.steps_since_meal >= self.LEAVE_CAVE_AT and not (finisher and c.steps_since_meal < self.LEAVE_CAVE_AT + 1):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```