

The only remaining **required** failures are the two `initial_wheat=15` configs (dragon survives 30 steps). Root cause: my meal reserve `upcoming_meals` counted *every* villager with `ssm≥3`, which over‑withholds wheat and blocks warrior spawning exactly when wheat is scarce. With no warriors spawned early enough, the dragon regenerates and never dies.

Fixes:
- **Tighter reserve**: only reserve wheat for villagers that are *imminently* going to eat (`ssm ≥ 5`), since farmers produce 5 wheat/step which covers the slower 3‑4‑step eaters easily.
- **Aggressive pipeline**: when `total_warriors == 0`, spawn a warrior pair as soon as 12 wheat exists (zero attackers ⇒ guaranteed loss), ignoring the farming reserve.
- Keep ≥1 farming pair only when we already have some warriors; relax it when warriors are scarce.
- All other passing behavior (eating cycles, cave leave at `ssm≥4`, endgame farmer attacks) is preserved.

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat_left = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)
        dragon_hp = environment.dragon.hp

        # Bucket each component into exactly one category
        must_eat = []
        eat_reset = []
        to_cave = []
        farmers_avail = []

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.role == "Warrior" and c.steps_since_meal >= 2:
                eat_reset.append(c)
            elif c.role == "Warrior":
                to_cave.append(c)
            else:
                farmers_avail.append(c)

        # Critical eaters
        for c in must_eat:
            if wheat_left >= 1:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                environment.assign_group(c, "farm")

        # Warriors resetting food cycle (arrive fresh for a full attack rotation)
        for c in eat_reset:
            if wheat_left >= 1:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                environment.assign_group(c, "farm")

        # Fresh warriors head to the cave
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # --- Farmer decisions ---
        # Reserve only for imminent meals (villagers about to eat next step).
        # Slower eaters (ssm 3-4) are covered by ongoing farming output.
        imminent = 0
        for v in environment.warriors + environment.farmers:
            if v.steps_since_meal >= 5:
                imminent += 1

        n_farm = len(farmers_avail)
        pairs = 0

        if total_warriors == 0:
            # Critical: no attackers at all. Spawn as soon as we can pay 12.
            while pairs + 1 <= n_farm // 2 and wheat_left >= 12:
                pairs += 1
        elif total_warriors < 6:
            while (pairs + 1 <= n_farm // 2
                   and (n_farm - 2 * (pairs + 1)) >= 1
                   and wheat_left >= 12 + imminent):
                pairs += 1
            # If wheat would allow it but only farming reserve blocks, relax when few warriors
            if pairs == 0 and total_warriors <= 2 and wheat_left >= 12 and n_farm >= 2:
                pairs = min(n_farm // 2, 1)
        elif total_warriors < 10:
            if (n_farm >= 3 and wheat_left >= 12 + imminent):
                pairs = 1
        else:
            pairs = 0

        idx = 0
        for _ in range(pairs):
            if wheat_left >= 12 and idx + 1 < n_farm:
                environment.assign_group(farmers_avail[idx], "spawn warrior")
                environment.assign_group(farmers_avail[idx + 1], "spawn warrior")
                wheat_left -= 12
                idx += 2

        # Need more total villagers (wheat farm) if cheap to do so
        if total_villagers < 5 and (n_farm - idx) >= 2 and pairs == 0 and wheat_left >= 10 + imminent:
            environment.assign_group(farmers_avail[idx], "spawn farmer")
            environment.assign_group(farmers_avail[idx + 1], "spawn farmer")
            idx += 2

        # Remaining available farmers farm
        for i in range(idx, n_farm):
            environment.assign_group(farmers_avail[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 4:
                # Travel 1 step -> arrive village at ssm 5 -> eat that step (before ssm 6)
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            elif dragon_hp <= 15 and c.steps_since_meal <= 2:
                # Endgame: throw everyone with fresh food at the dragon to finish fast
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "attack")
```