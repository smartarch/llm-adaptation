

Looking at the failures carefully:

1. **System test**: The `affordable()` function used *future* farming output to justify spending wheat now, but the game checks wheat at assignment time. Also, farmers left unassigned when spawn logic was too restrictive.
2. **Dragon not killed**: Not enough warriors attacking due to overly cautious spawn gating.
3. **Key insight**: I must track wheat as a running budget (`wheat_left`) that decrements with each meal and spawn assignment. Farming output from the current step is NOT yet available when checking spawn costs.

Strategy:
- Running wheat budget: decrement on each eat/spawn. Check against this for all costs.
- Warriors: ssm ≥ 4 → eat, ssm ≥ 2 → eat (reset for full attack cycle), ssm ≤ 1 → cave
- Cave: ssm ≥ 4 → leave, else attack
- Farmers: try spawning warriors with simple wheat check, rest farm
- If < 5 villagers total, spawn a farmer pair if affordable
- Endgame (dragon ≤ 15): send all healthy villagers to cave

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

        # Critical eaters: eat if affordable, else farm
        for c in must_eat:
            if wheat_left >= 1:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                environment.assign_group(c, "farm")

        # Warriors resetting food cycle for full attack rotation
        for c in eat_reset:
            if wheat_left >= 1:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                environment.assign_group(c, "farm")

        # Fresh warriors go to cave (unless endgame, handled below)
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # --- Farmer decisions ---
        # Count how many villagers will need meals in the next ~3 steps
        # so we keep a reserve
        upcoming_meals = 0
        for v in environment.warriors + environment.farmers:
            if v.steps_since_meal >= 3:
                upcoming_meals += 1

        # Try to spawn warriors: need 2 farmers and 12 wheat per pair
        # Reserve upcoming_meals worth of wheat
        reserve = upcoming_meals
        available_for_spawn = wheat_left - reserve
        max_pairs = min(len(farmers_avail) // 2, available_for_spawn // 12)
        # Keep at least 1 farmer farming if possible (for production)
        if len(farmers_avail) >= 2 and total_warriors > 2:
            max_pairs = min(max_pairs, (len(farmers_avail) - 1) // 2)
        # If very few warriors, allow using all spare farmers for spawning
        if total_warriors <= 1:
            max_pairs = min(len(farmers_avail) // 2, available_for_spawn // 12)
        # If < 5 villagers, also consider farmer spawns (10 wheat)
        if total_villagers < 5 and max_pairs == 0 and len(farmers_avail) >= 2:
            if available_for_spawn >= 10:
                environment.assign_group(farmers_avail[0], "spawn farmer")
                environment.assign_group(farmers_avail[1], "spawn farmer")
                # Remaining farmers farm
                for i in range(2, len(farmers_avail)):
                    environment.assign_group(farmers_avail[i], "farm")
                return

        idx = 0
        pairs_to_spawn = min(max_pairs, len(farmers_avail) // 2)
        # Limit aggressive spawning: don't spawn more than needed
        if total_warriors >= 8:
            pairs_to_spawn = min(pairs_to_spawn, 1)
        elif total_warriors >= 12:
            pairs_to_spawn = 0

        for _ in range(pairs_to_spawn):
            if wheat_left >= 12 and idx + 1 < len(farmers_avail):
                environment.assign_group(farmers_avail[idx], "spawn warrior")
                environment.assign_group(farmers_avail[idx + 1], "spawn warrior")
                wheat_left -= 12
                idx += 2

        for i in range(idx, len(farmers_avail)):
            environment.assign_group(farmers_avail[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            elif dragon_hp <= 15 and c.role == "Farmer" and c.steps_since_meal <= 2:
                # Endgame: even farmers attack if they won't starve
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "attack")
```