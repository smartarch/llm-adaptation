from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        assigned = {}

        # --- Phase 1: Must eat (sme >= 5 is critical, sme == 4 is safe buffer) ---
        for c in components:
            if c.steps_since_meal >= 5:
                assigned[id(c)] = "eat"
            elif c.steps_since_meal == 4 and wheat >= 2:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if id(c) not in assigned]

        # --- Phase 2: Endgame dump ---
        # Calculate total damage achievable if everyone goes to cave NOW
        # (includes villagers already in cave who can still attack)
        all_alive = [v for v in environment.warriors + environment.farmers if v.hp > 0]
        in_cave_attackable = [v for v in all_alive if v.location == "Cave" and v.steps_since_meal <= 3]
        est_damage = sum(3 if v.role == "Warrior" else 1 for v in in_cave_attackable)
        for c in remaining:
            if c.role == "Warrior":
                # Will arrive sme=2, attack sme=2,3 = 6 damage
                est_damage += 6
            else:
                est_damage += 4  # arrive sme=2/3, attack 1-2 times
        if dragon_hp > 0 and dragon_hp <= est_damage:
            for c in remaining:
                if c.hp >= 1:
                    assigned[id(c)] = "cave"
            for c in remaining:
                if id(c) not in assigned:
                    assigned[id(c)] = "farm"
            for c in components:
                environment.assign_group(c, assigned[id(c)])
            return

        # --- Phase 3: Spawn warriors aggressively (first ~10 steps) ---
        total_warriors = sum(1 for v in environment.warriors if v.hp > 0)
        total_farmers = sum(1 for v in environment.farmers if v.hp > 0)
        spawn_warrior = []
        spawn_farmer = []

        # Count villagers in village who are NOT eating
        farmers_in_village = [c for c in remaining if c.role == "Farmer"]

        if step <= 12 and total_warriors < 7 and wheat >= 14:
            # Use pairs of villagers to spawn warriors
            while (len(farmers_in_village) >= 3 and  # keep 1 farming
                   wheat >= 13 and
                   total_warriors + len(spawn_warrior) // 2 < 7):
                a = farmers_in_village[0]
                b = farmers_in_village[1]
                # Only spawn if they won't starve (sme <= 3, they'll eat next cycle)
                if a.steps_since_meal <= 3 and b.steps_since_meal <= 3:
                    spawn_warrior.extend([a, b])
                    farmers_in_village.pop(0)
                    farmers_in_village.pop(0)
                    wheat -= 12
                    total_warriors += 1
                else:
                    break

        if total_farmers < 2 and len(farmers_in_village) >= 2 and wheat >= 12:
            spawn_farmer.extend([farmers_in_village[0], farmers_in_village[1]])
            farmers_in_village.pop(0)
            farmers_in_village.pop(0)
            wheat -= 10

        for c in spawn_warrior:
            assigned[id(c)] = "spawn warrior"
        for c in spawn_farmer:
            assigned[id(c)] = "spawn farmer"

        remaining = [c for c in components if id(c) not in assigned]

        # --- Phase 4: Determine who will attack next step to prevent regen ---
        # Count villagers who will be attacking THIS step (already in cave, sme<=3)
        cur_attackers = sum(1 for v in in_cave_attackable)

        # Count villagers traveling TO cave (assigned "cave" in village last step)
        # They arrive next step with sme=2 and attack sme=2.
        # Count villagers in village at sme<=1 who will be sent to cave:
        # They arrive next step at sme=2, attack that step.

        # Send warriors to cave: prefer sme<=1 (get 2-3 attacks)
        warriors_available = sorted(
            [c for c in remaining if c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp >= 2],
            key=lambda x: x.steps_since_meal
        )
        for c in warriors_available:
            assigned[id(c)] = "cave"

        # Also send warriors at sme=2 if no one else will attack (1 attack is better than regen)
        remaining = [c for c in components if id(c) not in assigned]
        if cur_attackers + len(warriors_available) == 0:
            w2 = sorted(
                [c for c in remaining if c.role == "Warrior" and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda x: x.steps_since_meal
            )
            for c in w2[:2]:
                assigned[id(c)] = "cave"

        remaining = [c for c in components if id(c) not in assigned]

        # --- Phase 5: Send farmers to cave to fill attack gaps ---
        # If nobody will be attacking this step or next step, send a farmer
        farmers_in_cave_count = sum(1 for v in all_alive if v.location == "Cave" and v.role == "Farmer" and v.steps_since_meal <= 3)
        warriors_in_cave_sme3 = sum(1 for v in all_alive if v.location == "Cave" and v.role == "Warrior" and v.steps_since_meal == 3)
        # Villagers who will attack this step = those in cave with sme<=3
        will_attack_next_step = cur_attackers  # rough estimate
        
        fresh_farmers = sorted(
            [c for c in remaining if c.role == "Farmer" and c.steps_since_meal <= 2 and c.hp >= 2],
            key=lambda x: x.steps_since_meal
        )
        # Always try to keep at least 1 farmer going to cave to prevent regen gaps
        # But keep enough farming for wheat
        num_farmers_farming = sum(1 for v in environment.farmers if v.location == "Village" and v.hp > 0 and v.steps_since_meal < 4) - len(fresh_farmers)
        if num_farmers_farming > 1 and fresh_farmers:
            # Send 1 farmer to cave (especially if few attackers)
            if cur_attackers <= 1:
                assigned[id(fresh_farmers[0])] = "cave"
        elif num_farmers_farming > 2 and len(fresh_farmers) > 1:
            assigned[id(fresh_farmers[0])] = "cave"

        # --- Phase 6: Everyone else farms ---
        for c in remaining:
            if id(c) not in assigned:
                assigned[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp
        all_alive = [v for v in environment.warriors + environment.farmers if v.hp > 0]

        assigned = {}

        # Hard constraint: sme >= 4 must go to village
        for c in components:
            if c.steps_since_meal >= 4:
                assigned[id(c)] = "village"
            elif c.hp <= 1:
                assigned[id(c)] = "village"

        # Everyone else attacks
        for c in components:
            if id(c) not in assigned:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])