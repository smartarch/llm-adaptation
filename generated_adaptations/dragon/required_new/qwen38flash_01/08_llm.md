

Looking at the failures, I can identify two critical bugs:

1. **Hunger constraint violated**: In the cave, `sme >= 4` must trigger a return to village (not `>= 5`). A villager at `sme=4` in the cave must leave NOW because they need 1 step to travel and must eat at `sme=5` (before starving at `sme=6`).

2. **Components not assigned**: My filtering logic was dropping components due to complex list mutations and the `late_game`/spawning blocks not properly tracking all assignments.

**Fix strategy:**
- Rewrite with a simple priority-based system where every component gets exactly one assignment
- In cave: `sme >= 4` → village (mandatory, no exceptions)
- In village: `sme >= 5` → eat (mandatory); `sme >= 4` → eat (safe); others get assigned to farm/cave/spawn
- Aggressive warrior spawning in first 8 steps to get 3+ warriors attacking ASAP
- Staggered cave sends to maintain continuous attack pressure

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

        # Track assignments to ensure each component gets exactly one
        assigned = {id(c): None for c in components}

        # Count how many villagers can currently attack in the cave
        in_cave_attackers = 0
        for v in (environment.warriors + environment.farmers):
            if v.location == "Cave" and v.steps_since_meal < 4 and v.hp > 0:
                in_cave_attackers += 1

        # Priority 1: Must eat (sme >= 5 means starving next step; sme >= 4 is safe)
        # Also: in cave at sme >= 4 they MUST be in village, so if they're here with sme >= 4, eat
        for c in components:
            if c.steps_since_meal >= 4 and assigned[id(c)] is None:
                assigned[id(c)] = "eat"

        # Priority 2: Spawn warriors aggressively in early game
        # Use pairs of villagers (preferably farmers) to spawn
        if step <= 8:
            available_spawn = [c for c in components if assigned[id(c)] is None and c.role == "Farmer"]
            # Try to spawn warriors while wheat allows
            while (len(available_spawn) >= 2 and
                   wheat >= 14 and
                   len([v for v in environment.warriors if v.hp > 0]) < 5):
                c1 = available_spawn.pop(0)
                c2 = available_spawn.pop(0)
                assigned[id(c1)] = "spawn warrior"
                assigned[id(c2)] = "spawn warrior"
                wheat -= 12

        # Priority 3: Send warriors to cave to maintain attackers
        # Keep ~2-3 attackers in cave at all times
        target_attackers = 3 if step > 3 else 2
        to_send = target_attackers - in_cave_attackers

        if to_send > 0 and not (step >= 25 and dragon_hp <= 0):
            # Prefer warriors with low sme and good hp
            eligible = sorted(
                [c for c in components if assigned[id(c)] is None and c.role == "Warrior"],
                key=lambda c: (c.steps_since_meal, -c.hp)
            )
            for c in eligible[:to_send]:
                assigned[id(c)] = "cave"

            # If still need attackers, send a farmer
            if in_cave_attackers + min(to_send, len(eligible)) == 0:
                farmer_eligible = [c for c in components if assigned[id(c)] is None and c.role == "Farmer" and c.steps_since_meal <= 1]
                if farmer_eligible:
                    assigned[id(farmer_eligible[0])] = "cave"

        # Priority 4: Late game push (step >= 22) - send everyone who can fight
        if step >= 22:
            for c in components:
                if assigned[id(c)] is None and c.hp > 0 and c.steps_since_meal <= 3:
                    assigned[id(c)] = "cave"

        # Priority 5: Everyone remaining farms
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "farm"

        # Execute all assignments
        for c in components:
            environment.assign_group(c, assigned[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        late_game = step >= 24
        dragon_hp = environment.dragon.hp

        assigned = {id(c): None for c in components}

        # Priority 1: Must return to village if sme >= 4 (CRITICAL CONSTRAINT)
        # At sme=4, travel 1 step to village, arrive at sme=5, must eat (sme=6 = starve)
        for c in components:
            if c.steps_since_meal >= 4:
                assigned[id(c)] = "village"
            elif c.hp <= 1:
                assigned[id(c)] = "village"

        # Priority 2: Everyone else attacks
        # In late game with low dragon HP, be more aggressive (allow sme=3 to push)
        for c in components:
            if assigned[id(c)] is None:
                if late_game and dragon_hp <= 15:
                    # Push harder in endgame
                    if c.steps_since_meal >= 5 or c.hp <= 0:
                        assigned[id(c)] = "village"
                    else:
                        assigned[id(c)] = "attack"
                else:
                    if c.steps_since_meal >= 4:
                        assigned[id(c)] = "village"
                    else:
                        assigned[id(c)] = "attack"

        # Safety: ensure everyone is assigned
        for c in components:
            if assigned[id(c)] is None:
                assigned[id(c)] = "attack"

        # Execute
        for c in components:
            environment.assign_group(c, assigned[id(c)])
```