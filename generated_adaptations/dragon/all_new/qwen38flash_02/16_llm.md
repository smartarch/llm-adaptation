

The catastrophic regression (0% win rate) came from my `dragon_hp <= 30` endgame block: it sent **all** villagers—including those needing food—to the cave, where they couldn't eat and all starved/died. The broken spawn gate also starved the warrior pipeline.

I'm reverting to the proven eating/spawn logic (which passed all required constraints) and removing the lethal endgame block. Speed is improved by being more aggressive on early warrior spawning while still keeping the wheat-reserve that prevents starvation, and by spawning a farmer when total villagers < 5.

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)
        total_villagers = total_warriors + total_farmers

        # Bucket each component into exactly one category (covers all cases)
        must_eat = []       # ssm >= 4: will starve soon, must eat NOW (or farm if no wheat)
        eat_reset = []      # warriors with ssm 2-3: eat to reset for a full 3-attack cave cycle
        to_cave = []        # warriors with ssm <= 1: go to cave (arrive with ssm <= 2)
        farmers_avail = []  # farmers with ssm <= 3: farm or spawn

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.role == "Warrior" and c.steps_since_meal >= 2:
                eat_reset.append(c)
            elif c.role == "Warrior":
                to_cave.append(c)
            else:
                farmers_avail.append(c)

        eat_count = 0

        # Critical eaters
        for c in must_eat:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "farm")

        # Warriors resetting their food cycle (so they get a full 3-attack rotation)
        for c in eat_reset:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "farm")

        # Fresh warriors head to the cave
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # --- Farmer decisions: spawn warriors / spawn farmer / farm ---
        # Wheat remaining after this step's meals
        after_eats = wheat - eat_count

        # Reserve for meals that will come due soon (villagers approaching ssm 6)
        upcoming_meals = 0
        for v in environment.warriors + environment.farmers:
            if v.steps_since_meal >= 3:
                upcoming_meals += 1

        # Each spawned warrior consumes a farmer pair and 12 wheat now.
        # Determine the largest number of warrior-pairs we can afford while
        # leaving enough wheat (after farming output) to cover upcoming meals.
        max_pairs = len(farmers_avail) // 2

        def affordable(pairs):
            farm_count = len(farmers_avail) - 2 * pairs
            farm_output = 5 * max(0, farm_count)
            remaining = after_eats - 12 * pairs + farm_output
            return remaining >= upcoming_meals

        spawn_warrior_pairs = 0
        if total_warriors == 0:
            # Critical: no attackers at all, spawn as much as wheat safely allows
            while spawn_warrior_pairs + 1 <= max_pairs and affordable(spawn_warrior_pairs + 1):
                spawn_warrior_pairs += 1
        elif total_warriors < 8:
            while spawn_warrior_pairs + 1 <= max_pairs and affordable(spawn_warrior_pairs + 1):
                spawn_warrior_pairs += 1
        elif total_warriors < 12 and affordable(spawn_warrior_pairs + 1):
            spawn_warrior_pairs += 1

        # Leave at least one farming pair (2 farmers) for production if possible
        keep_farming = 2
        max_by_farmers = (len(farmers_avail) - keep_farming) // 2
        if max_by_farmers >= 0:
            spawn_warrior_pairs = min(spawn_warrior_pairs, max_by_farmers)
        # But if there are almost no warriors, allow dropping the farming reserve
        if total_warriors <= 2 and max_pairs > 0:
            spawn_warrior_pairs = max(spawn_warrior_pairs,
                                      min(max_pairs, max(0, (len(farmers_avail) - 0) // 2)))
            while spawn_warrior_pairs > 0 and not affordable(spawn_warrior_pairs):
                spawn_warrior_pairs -= 1

        idx = 0
        for _ in range(spawn_warrior_pairs):
            environment.assign_group(farmers_avail[idx], "spawn warrior")
            environment.assign_group(farmers_avail[idx + 1], "spawn warrior")
            idx += 2

        # If still very few total villagers and wheat comfortably allows, add a farmer
        if total_villagers < 5 and (len(farmers_avail) - idx) >= 2 and spawn_warrior_pairs == 0:
            farm_count = (len(farmers_avail) - idx) - 2
            farm_output = 5 * max(0, farm_count)
            remaining = after_eats - 10 + farm_output
            if remaining >= upcoming_meals:
                environment.assign_group(farmers_avail[idx], "spawn farmer")
                environment.assign_group(farmers_avail[idx + 1], "spawn farmer")
                idx += 2

        # All remaining available farmers farm
        for i in range(idx, len(farmers_avail)):
            environment.assign_group(farmers_avail[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Leave now: travel (1) arrives village at ssm 5, eat that step (< 6)
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```