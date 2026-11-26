**Analysis:** all constraints pass now — the remaining failures are just losing games. We're not dealing enough damage. Key math: the Dragon has 100 HP, regenerates 5/step only when nobody attacked that step. The win at seed=2 came from a sustained assault. Improvements:

1. **Attack earlier and with everyone:** start the assault at step 6 with even 2 warriors — 2 attacks/step beats stopping regeneration, and more warriors trickle in over time.
2. **Much more spawning:** raise the warrior cap to 20 and spawn aggressively whenever wheat exceeds the food reserve; every spawned warrior adds sustained damage.
3. **Hunger cycle tightened:** warriors eat in the village at hunger 4, return to the cave — with travel and eating in consecutive steps, a warrior attacks ~5 of every 7 steps. With enough warriors this outdamages regeneration consistently.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 4          # eat in village when this hungry
    LEAVE_CAVE_AT = 3   # leave cave when this hungry (arrive home at 4, eat)
    WARRIOR_CAP = 20

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)

        assault = total_warriors >= 2 or step >= 6
        emergency = step >= 24 and total_warriors > 0

        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # ---- spawn planning (with food reserve) ----
        reserve = hungry_count + 4
        budget = max(0, wheat - reserve)
        w_pairs = 0
        f_pairs = 0
        if not emergency:
            if step < 6 and total_villagers < 9:
                f_pairs = max(0, min(1, (budget - 16) // 10))
                budget -= f_pairs * 10
            if total_warriors < self.WARRIOR_CAP:
                w_pairs = max(0, min(3, budget // 12))

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
                environment.assign_group(c, "cave" if (assault or emergency) else "farm")
                continue

            # 4) farmers: farm to feed the war; join late push only if safe
            if emergency and c.steps_since_meal <= 2 and wheat >= 6:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= self.LEAVE_CAVE_AT:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```