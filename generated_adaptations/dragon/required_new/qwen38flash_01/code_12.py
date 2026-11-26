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
        # Villagers currently attacking in cave
        cur_attackers = sum(1 for v in in_cave if v.steps_since_meal <= 3)
        # Villagers in pipeline (cave or about-to-travel): count cave members who will still attack
        # We'll treat "in_cave" as the pipeline. We want ~6 in pipeline at steady state.
        pipeline = len(in_cave)

        # ---- Priority 1: eat ----
        # sme >= 4 in village: must eat soon; if sme >= 5 mandatory. sme == 4 still ok to farm
        # but if wheat is plenty, eat now to free up.
        for c in components:
            if c.steps_since_meal >= 4:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if assigned[id(c)] is None]

        # ---- Priority 2: endgame dump ----
        # Estimate remaining attack potential if everyone dumped now
        total_dump_dmg = 0
        for c in remaining:
            if c.role == "Warrior":
                total_dump_dmg += 3
            else:
                total_dump_dmg += 1
        # plus already-in-cave attackers
        for v in in_cave:
            if v.steps_since_meal <= 3:
                total_dump_dmg += 3 if v.role == "Warrior" else 1

        if step >= 18 and dragon_hp <= total_dump_dmg and dragon_hp > 0:
            for c in remaining:
                if c.hp >= 1:
                    assigned[id(c)] = "cave"
            for c in components:
                if assigned[id(c)] is None:
                    assigned[id(c)] = "eat"
            for c in components:
                environment.assign_group(c, assigned[id(c)])
            return

        # ---- Priority 3: spawn warriors aggressively early ----
        total_warriors_alive = sum(1 for v in environment.warriors if v.hp > 0)
        total_farmers_alive = sum(1 for v in environment.farmers if v.hp > 0)
        target_warriors = 7

        spawn_warrior = []
        spawn_farmer = []

        if step <= 12 and not (step >= 18 and dragon_hp <= total_dump_dmg):
            # Use pairs of farmers as spawners (they produce 5/step, sacrifice 1 step to make warrior)
            farmer_pool = [c for c in remaining if c.role == "Farmer" and assigned[id(c)] is None]
            # reserve enough farmers to keep wheat up: at least 2 farming in mid-game
            reserve = 2 if step > 3 else 1
            while (wheat >= 14 and len(farmer_pool) - len(spawn_warrior) >= 2
                   and (len(farmer_pool) - len(spawn_warrior)) > reserve
                   and total_warriors_alive + len(spawn_warrior) // 2 < target_warriors):
                a = farmer_pool[len(spawn_warrior)]
                b = farmer_pool[len(spawn_warrior) + 1]
                spawn_warrior.extend([a, b])
                total_warriors_alive += 1
                wheat -= 12

            # Spawn a farmer if critically low
            if total_farmers_alive - len(spawn_warrior) // 2 < 2 and len(farmer_pool) >= 4 and wheat >= 11:
                # don't overdo, skip in early game when wheat tight
                pass

        for c in spawn_warrior:
            assigned[id(c)] = "spawn warrior"
        for c in spawn_farmer:
            assigned[id(c)] = "spawn farmer"

        remaining = [c for c in components if assigned[id(c)] is None]

        # ---- Priority 4: send 1 warrior to cave per step (staggered) ----
        # Send a fresh warrior (sme <= 1) if pipeline < ~6 and we have attackers available
        max_pipeline = 6 if step < 20 else 3
        can_send = max(0, max_pipeline - pipeline)
        if can_send > 0:
            fresh_warriors = sorted(
                [c for c in remaining if c.role == "Warrior"
                 and c.steps_since_meal <= 1 and c.hp >= 2],
                key=lambda c: c.steps_since_meal,
            )
            for c in fresh_warriors[:can_send]:
                assigned[id(c)] = "cave"
                pipeline += 1

        # If nobody will be attacking in cave next step and we have a fresh farmer, send one
        if cur_attackers == 0 and pipeline == 0:
            fresh_farmers = [c for c in remaining
                             if c.role == "Farmer" and c.steps_since_meal <= 1 and c.hp >= 2
                             and assigned[id(c)] is None]
            if fresh_farmers and len(fresh_farmers) > 1:
                # keep at least 1 farmer farming
                assigned[id(fresh_farmers[0])] = "cave"

        # ---- Priority 5: mid-game extra sends if we have lots of warriors ----
        if (step >= 5 and step < 20 and pipeline < 4 and wheat >= 25):
            extras = [c for c in remaining
                      if c.role == "Warrior" and c.steps_since_meal <= 2
                      and c.hp >= 3 and assigned[id(c)] is None]
            for c in extras[:1]:
                assigned[id(c)] = "cave"

        # ---- Priority 6: everyone else farms ----
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp
        assigned = {id(c): None for c in components}

        # Hard deadline: sme >= 4 → must leave to village (arrive sme=5, eat).
        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 1:
                assigned[id(c)] = "village"

        # Everyone else attacks (sme <= 3).
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])