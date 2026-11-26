

The core issue is the dragon isn't dying. Analyzing the math: with `sme>=4` forcing a return from cave, warriors get exactly 3 attack steps per 6-step cycle. The dragon regenerates 5 HP/step **only when nobody attacks**. So even 1 attacker prevents all regen. The critical insight: I need **staggered sends** (1 warrior/step) so 3 warriors are always simultaneously in the cave at sme=1,2,3, dealing 9 dmg/step with 0 regen → kill in ~12 attack-steps. My previous code sent ALL warriors simultaneously, creating gaps.

New plan:
- **Send exactly 1 warrior per step** to cave (creating a pipeline of 3 simultaneous attackers)
- **Spawn warriors aggressively** in first 8 steps to reach 6 warriors (for continuous pipeline)
- **Farmers fill gaps** when no warrior is attacking
- **Endgame**: dump everyone when dragon HP ≤ total available damage
- **Cave**: `sme>=4` → village, everything else attacks (sme=3 is the last attack, sme=4 must leave)

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

        all_villagers = environment.warriors + environment.farmers
        alive = [v for v in all_villagers if v.hp > 0]
        in_cave = [v for v in alive if v.location == "Cave"]
        in_village = [v for v in alive if v.location == "Village"]

        # Count how many will be attacking THIS step (already in cave, sme<=3)
        cur_attackers = sum(1 for v in in_cave if v.steps_since_meal <= 3)

        # --- Mandatory eat ---
        for c in components:
            if c.steps_since_meal >= 4:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if assigned[id(c)] is None]

        # --- Endgame dump ---
        # Estimate total damage if everyone sends to cave this step
        est_damage = 0
        for v in in_cave:
            if v.steps_since_meal <= 3:
                est_damage += (3 if v.role == "Warrior" else 1)
        for c in remaining:
            est_damage += (3 if c.role == "Warrior" else 1)

        if dragon_hp > 0 and est_damage >= dragon_hp and step >= 8:
            for c in remaining:
                if c.hp >= 1:
                    assigned[id(c)] = "cave"
            for c in components:
                if assigned[id(c)] is None:
                    assigned[id(c)] = "eat" if c.steps_since_meal >= 3 else "farm"
            for c in components:
                environment.assign_group(c, assigned[id(c)])
            return

        # --- Spawn warriors aggressively (steps 1-10) ---
        total_warriors = sum(1 for v in environment.warriors if v.hp > 0)
        target_w = 7
        spawn_warrior = []

        if step <= 10 and total_warriors < target_w:
            # Use pairs of farmers as spawners
            farmer_pool = [c for c in remaining
                           if c.role == "Farmer" and assigned[id(c)] is None]
            # Reserve at least 2 farmers for farming
            while (len(farmer_pool) - len(spawn_warrior) >= 2 + 2 and
                   wheat - 12 >= 5 and
                   total_warriors + len(spawn_warrior) // 2 < target_w):
                a = farmer_pool[len(spawn_warrior)]
                b = farmer_pool[len(spawn_warrior) + 1]
                if a.steps_since_meal <= 1 and b.steps_since_meal <= 1:
                    spawn_warrior.extend([a, b])
                    wheat -= 12
                    total_warriors += 1
                else:
                    break

        for c in spawn_warrior:
            assigned[id(c)] = "spawn warrior"
        remaining = [c for c in components if assigned[id(c)] is None]

        # --- Send warriors to cave: staggered, ~1 per step ---
        # Goal: maintain 3 attackers in cave at sme=1,2,3
        # Count future attackers: those in cave with sme<=2 will attack next step too
        future_attackers = sum(1 for v in in_cave if v.steps_since_meal <= 2)
        # If we send 1 warrior now, they arrive next step (sme=1) and attack for 3 steps
        # We want future_attackers + newly_sent >= 3 over time
        # Simple: send 1 fresh warrior if we have < 3 attackers currently or next step
        if step <= 2:
            # Early: send all warriors immediately to start the pipeline
            for c in remaining:
                if c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp >= 2:
                    assigned[id(c)] = "cave"
        else:
            # Stagger: send at most 1-2 warriors per step
            fresh_w = sorted(
                [c for c in remaining
                 if c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp >= 2],
                key=lambda x: x.steps_since_meal,
            )
            send_limit = 2 if cur_attackers <= 1 else 1
            for c in fresh_w[:send_limit]:
                assigned[id(c)] = "cave"

        remaining = [c for c in components if assigned[id(c)] is None]

        # --- If cave has zero attackers, send a farmer to prevent regen ---
        if cur_attackers == 0:
            fresh_f = [c for c in remaining
                       if c.role == "Farmer" and c.steps_since_meal <= 2 and c.hp >= 2]
            if len(fresh_f) > 1:
                assigned[id(fresh_f[0])] = "cave"

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

        # At sme=4, must travel to village (arrive sme=5, eat next step before sme=6)
        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 1:
                assigned[id(c)] = "village"

        # Everyone else attacks (sme 0,1,2,3 are safe)
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])
```