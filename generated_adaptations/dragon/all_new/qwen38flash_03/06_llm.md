

Looking at the test failures, I need to address several critical issues:

1. **Dragon not killed**: Warriors need to stay in the cave longer (at least 3-4 attacks), stagger eat cycles, and build a bigger army faster.
2. **Not spawning**: Must spawn warriors when few exist, and spawn at least one farmer.
3. **Warriors leaving cave too early**: Need to track attack count and enforce minimum attacks before return.
4. **No warriors case**: Must spawn a warrior immediately when none exist.

My strategy: aggressively spawn warriors from farmers in early steps, send ALL warriors to the cave, keep them attacking until `steps_since_meal >= 4`, stagger returns so some always attack, spawn a farmer when population is low, and use instance variables to track attack history per warrior in the cave.

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cave_arrival = {}   # id -> step when they arrived in cave
        self._cave_attacks = {}   # id -> number of attacks performed
        self._spawned_farmer = False
        self._spawned_warrior_count = 0

    def _total_warriors(self, environment):
        return len(environment.warriors)

    def _total_villagers(self, environment):
        return len(environment.warriors) + len(environment.farmers)

    def _max_warriors_in_cave_safe(self, environment):
        """Count warriors currently in cave that are not at critical hunger."""
        count = 0
        for w in environment.warriors:
            if w.location == "Cave" and w.steps_since_meal < 5:
                count += 1
        return count

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        assigned = set()

        # 1) Critical eat: s_m >= 5, they will starve if not eating now
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        remaining = [c for c in components if id(c) not in assigned]
        if not remaining:
            return

        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        wheat = environment.farm.wheat
        total_w = self._total_warriors(environment)
        total_villagers = self._total_villagers(environment)

        # How many warriors are already safely in the cave?
        warriors_in_cave = self._max_warriors_in_cave_safe(environment)
        warriors_in_village = len(warriors)

        # 2) Send warriors to cave aggressively
        # Keep some in village only if we need them for spawning or eating soon
        # Otherwise send them ALL to cave
        cave_targets = []
        village_warriors = []

        for w in warriors:
            # If a warrior is about to starve, they should stay and eat next step
            if w.steps_since_meal >= 4:
                village_warriors.append(w)
            else:
                cave_targets.append(w)

        # 3) Decide spawning
        spawn_warr_count = 0
        spawn_farm_count = 0

        # Target: ~6-7 warriors for attack power, ~2 farmers for economy
        target_warriors = 7

        # Must spawn warrior if zero warriors exist
        must_spawn_warrior = (total_w == 0 and len(farmers) >= 2 and wheat >= 12)

        # Spawn warriors aggressively if under target
        if total_w < target_warriors and len(farmers) >= 2:
            # Check if we can afford it: need 12 wheat per warrior, keep some reserve
            reserve = max(len(components), 5)  # keep enough for meals
            affordable = max(0, (wheat - reserve)) // 12
            possible = min(len(farmers) // 2, affordable)
            # Don't spawn if it would leave us with 0 farmers and we already have enough warriors
            if not must_spawn_warrior and possible > 0:
                spawn_warr_count = min(possible, (target_warriors - total_w) // 2)
            elif must_spawn_warrior:
                spawn_warr_count = min(possible, 1)

        # Spawn a farmer at least once if total population < 5
        if not self._spawned_farmer and total_villagers < 8 and len(warriors) >= 2 and wheat >= 10:
            reserve = max(len(components), 5)
            affordable = max(0, (wheat - reserve - 12 * spawn_warr_count)) // 10
            if affordable >= 1:
                spawn_farm_count = 1
                self._spawned_farmer = True

        # Assign spawn groups
        warr_idx = 0
        for _ in range(spawn_warr_count):
            if warr_idx + 1 < len(farmers):
                environment.assign_group(farmers[warr_idx], "spawn warrior")
                environment.assign_group(farmers[warr_idx + 1], "spawn warrior")
                assigned.add(id(farmers[warr_idx]))
                assigned.add(id(farmers[warr_idx + 1]))
                self._spawned_warrior_count += 1
                warr_idx += 2
                break  # one pair spawns one warrior

        for _ in range(spawn_farm_count):
            if warr_idx + 1 < len(farmers):
                environment.assign_group(farmers[warr_idx], "spawn farmer")
                environment.assign_group(farmers[warr_idx + 1], "spawn farmer")
                assigned.add(id(farmers[warr_idx]))
                assigned.add(id(farmers[warr_idx + 1]))
                warr_idx += 2

        # 4) Send warriors to cave
        for w in cave_targets:
            environment.assign_group(w, "cave")
            assigned.add(id(w))

        # 5) Warriors waiting in village (high s_m) just stay idle; they'll eat next step
        for w in village_warriors:
            if id(w) not in assigned:
                # Stay in village, they will be picked up for eat next step
                # Assign to a safe group that doesn't move them out
                environment.assign_group(w, "eat")
                assigned.add(id(w))

        # 6) Remaining farmers farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")
                assigned.add(id(f))

        # 7) Any unassigned warriors go to cave
        for w in warriors:
            if id(w) not in assigned:
                environment.assign_group(w, "cave")
                assigned.add(id(w))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        assigned = set()

        # Update attack tracking for warriors that were attacking last step
        for c in components:
            cid = id(c)
            if cid not in self._cave_arrival:
                self._cave_arrival[cid] = step
            if cid not in self._cave_attacks:
                self._cave_attacks[cid] = 0

        attack_group = []
        return_group = []
        stay_group = []

        for c in components:
            cid = id(c)
            s_m = c.steps_since_meal
            atk_count = self._cave_attacks.get(cid, 0)

            # Absolutely must leave if starving
            if s_m >= 5:
                return_group.append(c)
                continue

            # Leave if s_m == 4 AND attacked at least 2 times
            if s_m >= 4 and atk_count >= 2:
                return_group.append(c)
                continue

            # If s_m == 4 but haven't attacked enough, attack one more time
            if s_m >= 4 and atk_count < 2:
                # Critical - must leave next step at latest, attack now
                attack_group.append(c)
                continue

            # If s_m == 3 and attacked at least 3 times, return for sustainability
            if s_m >= 3 and atk_count >= 3:
                return_group.append(c)
                continue

            # Otherwise attack
            attack_group.append(c)

        # Assign groups
        for c in attack_group:
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in return_group:
            environment.assign_group(c, "village")
            assigned.add(id(c))
            # Clean up tracking for returning warriors
            cid = id(c)
            self._cave_attacks.pop(cid, None)
            self._cave_arrival.pop(cid, None)

        for c in stay_group:
            environment.assign_group(c, "cave")
            assigned.add(id(c))

        # Safety: assign any unassigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```