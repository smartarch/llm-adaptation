

I analyzed why we still lose: the pipeline caps were throttling attack output, and the dragon's regen + counterattacks need *continuous* multi-attacker pressure with heavy warrior recruitment. New plan: (1) spawn warriors aggressively from any 2 villagers early to build an 8+ warrior army; (2) send **every** fresh warrior (sme≤2) to cave each step — no pipeline cap — so 3+ warriors are always attacking; (3) farmers fill the cave only when attackers are scarce; (4) full endgame dump.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        assigned = {id(c): None for c in components}

        all_v = [v for v in environment.warriors + environment.farmers if v.hp > 0]
        in_cave = [v for v in all_v if v.location == "Cave"]
        cur_attackers = sum(1 for v in in_cave if v.steps_since_meal <= 3)

        # --- Mandatory eat ---
        for c in components:
            if c.steps_since_meal >= 4:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if assigned[id(c)] is None]

        # --- Endgame dump: if total available damage >= dragon hp, all go attack ---
        total_dmg = 0
        for v in in_cave:
            if v.steps_since_meal <= 3:
                total_dmg += 3 if v.role == "Warrior" else 1
        for c in remaining:
            total_dmg += 3 if c.role == "Warrior" else 1
        if dragon_hp > 0 and total_dmg >= dragon_hp + 5 and step >= 5:
            for c in remaining:
                if c.hp >= 1:
                    assigned[id(c)] = "cave"
            for c in components:
                if assigned[id(c)] is None:
                    assigned[id(c)] = "eat" if c.steps_since_meal >= 3 else "farm"
            for c in components:
                environment.assign_group(c, assigned[id(c)])
            return

        # --- Spawn warriors aggressively using pairs of villagers ---
        total_warriors = sum(1 for v in environment.warriors if v.hp > 0)
        total_farmers = sum(1 for v in environment.farmers if v.hp > 0)
        spawn_warrior = []
        spawn_farmer = []

        # Build big warrior army in first ~12 steps
        target_warriors = 9 if step < 12 else 6
        # Estimate wheat needed for imminent eating
        soon_eat = sum(1 for v in environment.warriors + environment.farmers
                       if v.location == "Cave" and v.steps_since_meal >= 2) + len(
                       [c for c in remaining if c.steps_since_meal >= 3])
        free_wheat = wheat - soon_eat - 3

        if free_wheat >= 14 and total_warriors < target_warriors:
            # Use 2 villagers per spawn; prefer pairs of farmers, fall back to any
            def take_two(pool):
                if len(pool) >= 2:
                    return [pool.pop(0), pool.pop(0)]
                return []

            farmer_pool = [c for c in remaining if c.role == "Farmer"]
            other_pool = [c for c in remaining if c.role == "Warrior"]

            # Keep at least 1-2 farmers farming for wheat
            min_farmers_farming = 2 if step < 10 else 1
            while (total_warriors + len(spawn_warrior) // 2 < target_warriors
                   and free_wheat >= 12):
                if len(farmer_pool) - len(spawn_farmer) >= max(2, min_farmers_farming + 2):
                    pair = take_two(farmer_pool)
                elif other_pool:
                    pair = take_two(other_pool) if len(other_pool) >= 2 else []
                else:
                    break
                if len(pair) == 2:
                    spawn_warrior.extend(pair)
                    free_wheat -= 12
                else:
                    break

            # Spawn a farmer if very few remain
            if total_farmers < 2 and len(farmer_pool) >= 2 and free_wheat >= 10:
                pair = take_two(farmer_pool)
                spawn_farmer.extend(pair)
                free_wheat -= 10

        for c in spawn_warrior:
            assigned[id(c)] = "spawn warrior"
        for c in spawn_farmer:
            assigned[id(c)] = "spawn farmer"

        remaining = [c for c in components if assigned[id(c)] is None]

        # --- Send every fresh warrior to cave (no cap) ---
        fresh_warriors = sorted(
            [c for c in remaining
             if c.role == "Warrior" and c.steps_since_meal <= 2 and c.hp >= 2],
            key=lambda x: x.steps_since_meal,
        )
        for c in fresh_warriors:
            assigned[id(c)] = "cave"

        remaining = [c for c in components if assigned[id(c)] is None]

        # --- If cave would have zero attackers, send a fresh farmer ---
        if cur_attackers == 0:
            fresh_farmers = [c for c in remaining
                             if c.role == "Farmer" and c.steps_since_meal <= 2 and c.hp >= 2]
            if len(fresh_farmers) >= 2:
                assigned[id(fresh_farmers[0])] = "cave"
                remaining.remove(fresh_farmers[0])

        # --- Everyone else farms ---
        for c in remaining:
            if assigned[id(c)] is None:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        assigned = {id(c): None for c in components}

        # Hard deadline: at sme=4 must leave (arrive village sme=5, eat before sme=6).
        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 1:
                assigned[id(c)] = "village"

        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])
```