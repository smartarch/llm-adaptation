**Fixes made:**

1. **`test_all_assigned` bug:** when an odd number of spawn slots remained, villagers fell into the spawn branch but were never assigned any group (`continue` with no assignment). Now spawn assignments are only made in complete pairs, and any villager not used for spawning always falls through to a normal group (eat → cave → farm).
2. **Win-rate improvement:** the hunger cycle was costing too many attack steps — warriors went to the cave at hunger 3, arrived at 4, ate, traveled back at 5... eating only every other trip. Now warriors in the Village eat whenever they are home hungry, and the assault phase starts earlier (≥ 4 warriors or step ≥ 10), committing all warriors to the Cave continuously. Spawning stops once the assault begins so all wheat goes to feeding; an all-in emergency at step ≥ 22 sends even farmers to fight.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 4          # eat in village when this hungry
    LEAVE_CAVE_AT = 3   # leave cave when this hungry (arrive at 4, eat)
    WARRIOR_CAP = 14

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)

        emergency = step >= 22 and total_warriors > 0
        assault = total_warriors >= 4 or step >= 10 or emergency

        # spawn planning (only while there's still time to use the new units)
        spawn_w_pairs = 0
        spawn_f_pairs = 0
        if not emergency and step < 14:
            hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)
            reserve = hungry_count + 6
            budget = wheat - reserve
            if total_warriors < self.WARRIOR_CAP:
                # each warrior pair costs 12 wheat
                spawn_w_pairs = max(0, budget // 12)
                budget -= spawn_w_pairs * 12
            if total_villagers < 8 and step < 8:
                # each farmer pair costs 10 wheat, keep a buffer
                spawn_f_pairs = max(0, min(1, (budget - 8) // 10))

        w_left = spawn_w_pairs * 2
        f_left = spawn_f_pairs * 2

        for c in components:
            # 1) eating has top priority
            if c.steps_since_meal >= self.EAT_AT and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue

            # 2) spawn duties (only in complete pairs)
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

            # 3) warriors fight when the assault is on
            if c.role == "Warrior":
                environment.assign_group(c, "cave" if assault else "farm")
                continue

            # 4) farmers: farm (or join emergency assault)
            environment.assign_group(c, "cave" if emergency else "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= self.LEAVE_CAVE_AT:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```