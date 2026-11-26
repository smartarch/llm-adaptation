

Looking at the failures, the key problem is clear: my spawning logic is too conservative. When there are < 5 villagers or no warriors in the cave, I MUST spawn aggressively. The previous 100% win-rate version worked because it was more aggressive. I need to return to that aggressive approach while fixing the "Farmer should stay in Village" issue (don't send farmers to cave unless wheat is truly abundant).

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
        all_w = list(environment.warriors)
        all_f = list(environment.farmers)
        total = len(all_w) + len(all_f)
        num_w = len(all_w)
        w_in_cave = sum(1 for w in all_w if w.location == "Cave")

        assigned = set()

        # 1. Must eat (ssm >= 5, next step ssm=6 means starving)
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        # 2. Warriors with ssm <= 1 go to cave immediately (just ate, ready to travel)
        for c in components:
            if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        # 3. Spawn logic - AGGRESSIVE when < 5 villagers or low warrior count
        remaining = [c for c in components if id(c) not in assigned]

        # Need 2 villagers in spawn group
        # Prefer using farmers for spawning (warriors should attack)
        # Keep at least 1 farmer farming ONLY if we have enough warriors attacking

        need_more_warriors = num_w < 4 or w_in_cave < 3 or num_w == 0
        need_growth = total < 5
        should_spawn = need_growth or (need_more_warriors and num_w < 2)

        if should_spawn and len(remaining) >= 2:
            # Try to spawn a warrior first
            if wheat >= 12 + total:
                pool = [c for c in remaining if c.role == "Farmer"]
                if len(pool) < 2:
                    pool = remaining
                if len(pool) >= 2:
                    environment.assign_group(pool[0], "spawn warrior")
                    environment.assign_group(pool[1], "spawn warrior")
                    assigned.add(id(pool[0]))
                    assigned.add(id(pool[1]))
            elif total < 5 and wheat >= 10 + total:
                # Spawn a farmer to grow economy
                pool = [c for c in remaining if c.role == "Farmer"]
                if len(pool) >= 2:
                    environment.assign_group(pool[0], "spawn farmer")
                    environment.assign_group(pool[1], "spawn farmer")
                    assigned.add(id(pool[0]))
                    assigned.add(id(pool[1]))

        # 4. Remaining warriors with ssm <= 2 can still do a quick cave visit
        for c in components:
            if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        # 5. Everything remaining goes to farm (produce wheat)
        # Only send farmers to cave if wheat is truly abundant AND dragon is nearly dead
        for c in components:
            if id(c) not in assigned:
                if c.role == "Farmer" and dragon_hp <= 10 and wheat > total + 20:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        # ssm >= 4 in cave: must go to village NOW
        # Travel 1 step: arrive with ssm=5, eat next step (ssm goes 5->0). Safe.
        # ssm >= 5 in cave: already too late but send back immediately
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```