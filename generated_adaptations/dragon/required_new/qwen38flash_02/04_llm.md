

Looking at the failures, the main issues are:
1. **Attack coverage gaps**: When warriors return to eat, nobody attacks and the dragon regenerates 5 HP/step.
2. **Not spawning warriors aggressively enough** to maintain continuous attack coverage.
3. **Eating scheduling not optimized** for tight rotation cycles.

My new strategy:
- Maintain a strict warrior rotation cycle: send warriors with meal≤1, keep them attacking for 2-3 steps, return at meal≥4, eat at meal 5.
- Stagger warrior deployments to prevent simultaneous returns (which create attack gaps).
- Spawn warriors as aggressively as wheat allows since more warriors = more sustained DPS.
- In the cave, ALWAYS attack (never use "cave" idle group since dragon only counterattacks when attacked, and not attacking means 5 HP regen).
- Use "desperate mode" when dragon is low HP to throw everyone in.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._step_count = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        self._step_count = step

        # Observe cave occupancy
        cave_warriors = [w for w in environment.warriors if w.location == "Cave"]
        cave_farmers = [f for f in environment.farmers if f.location == "Cave"]
        total_warriors = len(environment.warriors)
        num_cave_attackers = len(cave_warriors) + len(cave_farmers)

        # Target number of attackers in cave for continuous coverage
        # With 3 attack steps per ~7-step cycle, need ~3 warriors for 1 continuous attacker
        # More warriors = more DPS but more risk of dragon eating them
        if dragon_hp <= 20:
            target_cave = total_warriors + len([f for f in environment.farmers if f.location == "Village" and f.hp >= 2])
        elif dragon_hp <= 50:
            target_cave = min(5, total_warriors)
        else:
            target_cave = min(4, max(2, total_warriors))

        need_more = max(0, target_cave - num_cave_attackers)

        assigned = set()

        # Priority 1: CRITICAL - must eat now (meal >= 5, will starve next step)
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        # Priority 2: URGENT eat (meal >= 4) - after any travel they'd hit 5-6
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        # Priority 3: Send warriors to cave (stagger: max 2 per step to avoid gaps)
        remaining = [c for c in components if id(c) not in assigned]
        warriors_village = [c for c in remaining if c.role == "Warrior"]
        warriors_village.sort(key=lambda w: w.steps_since_meal)

        max_send_this_step = max(1, (need_more + 1) // 2)  # stagger
        if num_cave_attackers == 0:
            max_send_this_step = need_more  # no attackers, send all available

        sent = 0
        for w in warriors_village:
            if sent >= max_send_this_step or sent >= need_more:
                break
            # Can safely travel+attack 2-3 steps if meal <= 2
            if w.steps_since_meal <= 2 and w.hp >= 2:
                environment.assign_group(w, "cave")
                assigned.add(id(w))
                sent += 1

        # If desperate (low dragon HP or no attackers), send even less-ready warriors
        if num_cave_attackers == 0 or (dragon_hp <= 30 and sent < need_more):
            for w in warriors_village:
                if id(w) in assigned:
                    continue
                if sent >= need_more:
                    break
                if w.steps_since_meal <= 3 and w.hp >= 1:
                    environment.assign_group(w, "cave")
                    assigned.add(id(w))
                    sent += 1

        # If desperate and no warriors left, send farmers to attack
        if num_cave_attackers == 0 and dragon_hp <= 40:
            remaining = [c for c in components if id(c) not in assigned]
            for c in remaining:
                if c.role == "Farmer" and c.steps_since_meal <= 2 and c.hp >= 2:
                    environment.assign_group(c, "cave")
                    assigned.add(id(c))
                    break

        # Priority 4: Spawn warriors aggressively
        remaining = [c for c in components if id(c) not in assigned]
        eat_count = sum(1 for c in components if c.steps_since_meal >= 4)
        wheat_after_eat = wheat - eat_count

        if wheat_after_eat >= 12 and len(remaining) >= 2 and total_warriors < 12:
            # Prefer to use farmers for spawning (warriors should farm/attack)
            farmers_avail = [c for c in remaining if c.role == "Farmer"]
            others_avail = [c for c in remaining if c.role != "Farmer"]

            spawn_picks = []
            for f in farmers_avail:
                if len(spawn_picks) >= 2:
                    break
                spawn_picks.append(f)
            for o in others_avail:
                if len(spawn_picks) >= 2:
                    break
                spawn_picks.append(o)

            if len(spawn_picks) >= 2:
                for s in spawn_picks:
                    environment.assign_group(s, "spawn warrior")
                    assigned.add(id(s))

        # Priority 5: Farm remaining villagers
        remaining = [c for c in components if id(c) not in assigned]
        for c in remaining:
            environment.assign_group(c, "farm")
            assigned.add(id(c))

        # Safety net
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        assigned = set()

        # Sort by meal urgency (highest first) so we decide who returns first
        sorted_comps = sorted(components, key=lambda c: -c.steps_since_meal)

        attackers_count = 0
        returning_count = 0

        for c in sorted_comps:
            if id(c) in assigned:
                continue

            # MUST return if starving imminent (meal >= 5 means next step is starvation)
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                returning_count += 1
                continue

            # Return if meal == 4 and not desperate (they'd hit 6 after travel)
            if c.steps_since_meal >= 4 and dragon_hp > 15:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                returning_count += 1
                continue

            # Return if very low HP (unless desperate to finish dragon)
            if c.hp <= 1 and dragon_hp > 12:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                returning_count += 1
                continue

            # Attack the dragon
            environment.assign_group(c, "attack")
            assigned.add(id(c))
            attackers_count += 1

        # Safety: ensure all assigned (default to attack)
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```