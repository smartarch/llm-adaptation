

Looking at the failures, the hunger constraints now pass, but the dragon isn't dying in 30 steps. Analyzing the math:

- A warrior can attack for only **3 steps** per trip (sme=1,2,3 in cave), then must leave at sme=4, travel back (sme=5), and eat. That's a 6-step cycle yielding 3 attacks = **0.5 attacks/step average** per warrior.
- Dragon regen is 5 HP/step whenever *nobody* attacks, so **continuous attack coverage is critical** — every gap costs ~6 HP net.
- A farmer in the cave deals 1 damage AND blocks 5 regen = huge value when no warrior can attack that step.
- Need ~4+ warriors sustained, built up in the first ~6 steps, with **staggered** cave entries so the cave is never empty.

Key fixes: (1) spawn warriors aggressively using farmer pairs in early steps; (2) send fresh warriors (sme≤2) to maintain ~3 attackers in cave each step; (3) send a farmer to cave whenever no warrior will be attacking to block regen; (4) all-in dump in the endgame; (5) never send a sme≥4 villager to cave (they couldn't make the round trip and eat).

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

        # Will everyone be assigned exactly once? Track by id.
        assigned = {id(c): None for c in components}

        all_v = environment.warriors + environment.farmers
        in_cave = [v for v in all_v if v.location == "Cave" and v.hp > 0]
        # Attackers currently able to attack (in cave, sme <= 3)
        cur_attackers = sum(1 for v in in_cave if v.steps_since_meal <= 3)

        endgame = step >= 22 and dragon_hp > 0

        # Priority 1: Must eat before starving (sme == 5). At sme>=6 they'd be starved.
        # Also a villager at sme==4 in village cannot make a cave round-trip in time, so
        # let them eat (cheap insurance) — but only if we have wheat; else farm.
        for c in components:
            if c.steps_since_meal >= 5:
                assigned[id(c)] = "eat"
        for c in components:
            if assigned[id(c)] is None and c.steps_since_meal == 4 and wheat >= 1:
                assigned[id(c)] = "eat"

        remaining = [c for c in components if assigned[id(c)] is None]

        # Priority 2: Aggressive warrior spawning in early/mid game using 2 villagers/step.
        total_warriors = sum(1 for v in environment.warriors if v.hp > 0)
        total_farmers = sum(1 for v in environment.farmers if v.hp > 0)
        spawn_warrior_pool = []
        spawn_farmer_pool = []

        # Prefer farmer pairs (they're less valuable in cave); keep >=1 farmer farming.
        def pick_pair(pool, n):
            out = []
            while len(out) < n and pool:
                out.append(pool.pop(0))
            return out

        if step <= 14 and not endgame and dragon_hp > 0:
            farmer_pool = [c for c in remaining if c.role == "Farmer"]
            # reserve 1-2 farmers for farming
            reserve = 1 if step > 4 else 2
            while (wheat >= 13 and
                   len(farmer_pool) > reserve and
                   total_warriors + len(spawn_warrior_pool) // 2 < 5):
                pair = pick_pair(farmer_pool, 2)
                if len(pair) == 2:
                    spawn_warrior_pool.extend(pair)
                    total_warriors += 1
                    wheat -= 12
            if total_farmers < 2 and wheat >= 11 and len(farmer_pool) >= 2:
                pair = pick_pair(farmer_pool, 2)
                if len(pair) == 2:
                    spawn_farmer_pool.extend(pair)
                    wheat -= 10

        # Priority 3: Send warriors/farmers to cave to maintain a steady attack stream.
        cave_pool = []
        # Fresh warriors are best for cave (sme <= 2 yields >=2 attacks per trip).
        fresh_warriors = sorted(
            [c for c in remaining if c.role == "Warrior"
             and c.steps_since_meal <= 2 and c.hp >= 2],
            key=lambda c: c.steps_since_meal,
        )
        # Target ~3 attackers present in cave going forward.
        target = 3 if step >= 2 else 2
        need = max(0, target - cur_attackers)
        for c in fresh_warriors:
            if need <= 0:
                break
            cave_pool.append(c)
            need -= 1

        # If nothing will be attacking in cave this step, send a farmer to block regen.
        if cur_attackers + len(cave_pool) == 0:
            fresh_farmers = [c for c in remaining if c.role == "Farmer"
                             and c.steps_since_meal <= 2 and c.hp >= 2]
            if fresh_farmers:
                cave_pool.append(fresh_farmers[0])

        # Priority 4: Endgame dump — everyone healthy sends to cave.
        if endgame:
            for c in remaining:
                if assigned[id(c)] is None and id(c) not in [id(x) for x in cave_pool]:
                    if c.hp >= 1 and c.steps_since_meal <= 4:
                        cave_pool.append(c)

        # Priority 5: Everyone left over farms.
        for c in remaining:
            if assigned[id(c)] is None:
                assigned[id(c)] = "farm"

        # Apply special groups.
        for c in spawn_warrior_pool:
            assigned[id(c)] = "spawn warrior"
        for c in spawn_farmer_pool:
            assigned[id(c)] = "spawn farmer"
        for c in cave_pool:
            assigned[id(c)] = "cave"

        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp
        endgame = step >= 24

        assigned = {id(c): None for c in components}

        # Must return when sme >= 4: travel 1 step to village (arrive sme=5), eat.
        # At sme=6 they would be starving, so leaving at sme=4 is the hard deadline.
        for c in components:
            if c.steps_since_meal >= 4 or c.hp <= 1:
                assigned[id(c)] = "village"

        # Everyone else attacks. In endgame, push a bit harder (leave at sme=5 is too
        # risky; keep the >=4 rule which already satisfies the constraint test).
        for c in components:
            if assigned[id(c)] is None:
                if endgame and dragon_hp <= 10 and c.steps_since_meal <= 4 and c.hp >= 2:
                    assigned[id(c)] = "attack"
                elif c.steps_since_meal <= 3:
                    assigned[id(c)] = "attack"
                else:
                    assigned[id(c)] = "village"

        # Safety net.
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "attack"

        for c in components:
            environment.assign_group(c, assigned[id(c)])
```