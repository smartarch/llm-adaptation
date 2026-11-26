

The previous "improved" version broke the required tests by being too conservative with spawning. I need to go back to the version that achieved 100% win rate, and only fix the minor issue of sending farmers to cave when wheat is very low.

Key fix: The spawning must be aggressive - always spawn when < 5 villagers and wheat >= cost + total_villagers. Don't send farmers to cave unless wheat is clearly surplus.

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

        # Phase 1: Must eat (ssm >= 5)
        must_eat = [c for c in components if c.steps_since_meal >= 5]
        not_eat = [c for c in components if c.steps_since_meal < 5]
        for c in must_eat:
            environment.assign_group(c, "eat")

        if not not_eat:
            return

        # Phase 2: Warriors with ssm <= 1 go to cave immediately
        cave_ready_warriors = [c for c in not_eat if c.role == "Warrior" and c.steps_since_meal <= 1]
        cave_ids = set(id(c) for c in cave_ready_warriors)
        for c in cave_ready_warriors:
            environment.assign_group(c, "cave")

        # Remaining in village (not eating, not going to cave yet)
        remaining = [c for c in not_eat if id(c) not in cave_ids]

        if not remaining:
            return

        # Phase 3: Spawning
        # "Enough wheat" = spawn_cost + total_villagers (one meal per villager reserve)
        farmers_remaining = [c for c in remaining if c.role == "Farmer"]
        warriors_remaining = [c for c in remaining if c.role == "Warrior"]

        # Keep at least min_farm farmers farming
        min_farm = 1 if total <= 3 else 2
        farmers_farm = farmers_remaining[:min_farm]
        farmers_extra = farmers_remaining[min_farm:]
        farm_ids = set(id(c) for c in farmers_farm)

        # Spawn pool = extra farmers + warriors that can't usefully go to cave
        spawn_pool = list(farmers_extra) + [c for c in warriors_remaining if c.steps_since_meal >= 3]

        can_spawn_farmer = total < 5 and wheat >= 10 + total and len(spawn_pool) >= 2
        can_spawn_warrior = (total < 5 or num_w < 3 or w_in_cave < 2) and wheat >= 12 + total and len(spawn_pool) >= 2

        spawned_count = 0
        if can_spawn_warrior:
            while len(spawn_pool) >= 2 + spawned_count * 2 and spawned_count < 2:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                environment.assign_group(c1, "spawn warrior")
                environment.assign_group(c2, "spawn warrior")
                spawned_count += 1
        elif can_spawn_farmer:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            spawned_count += 1
            # Try a second spawn if still under 5
            if total < 4 and len(spawn_pool) >= 2 and wheat >= 22 + total:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                environment.assign_group(c1, "spawn warrior")
                environment.assign_group(c2, "spawn warrior")
                spawned_count += 1

        spawned_ids = set()
        # Mark spawned from spawn_pool (they were removed from the list)
        # Actually we already assigned them. Need to track which components were assigned.
        # Re-collect: any component from spawn_pool that was popped is assigned.
        # Let me just re-scan remaining components and assign what's left.

        # Phase 4: Assign everything not yet assigned
        # Already assigned: must_eat (eat), cave_ready_warriors (cave), some from spawn_pool (spawn warrior/farmer)
        # Need to assign: farmers_farm (farm), warriors with ssm <= 2 (cave), rest (farm)

        # Warriors with ssm <= 2 can still make useful cave trips
        for c in warriors_remaining:
            if c.steps_since_meal <= 1:
                continue  # already assigned to cave
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Farmers that are farming
        for c in farmers_farm:
            environment.assign_group(c, "farm")

        # Extra farmers (from spawn_pool that weren't spawned)
        for c in farmers_extra:
            # Check if already assigned via spawn
            # We can't easily tell, so use a different approach:
            # If this farmer was in spawn_pool and got assigned, it won't reach here
            # because spawn_pool was modified. But farmers_extra wasn't modified.
            # Actually we need to track properly.
            pass

        # Let me redo this with proper tracking
        # Clear and redo all assignments from scratch
        # Actually we can't "unassign". Let me restructure.

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```

Wait, I have a structural bug - I'm assigning some things twice or not handling the spawn_pool overlap correctly. Let me rewrite cleanly:

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

        # Build assignment for each component
        assignments = {}  # id(c) -> group

        # Phase 1: Must eat (ssm >= 5)
        for c in components:
            if c.steps_since_meal >= 5:
                assignments[id(c)] = "eat"

        # Phase 2: Warriors with ssm <= 1 go to cave
        for c in components:
            if id(c) not in assignments and c.role == "Warrior" and c.steps_since_meal <= 1:
                assignments[id(c)] = "cave"

        # Phase 3: Spawning decisions
        # Get unassigned components
        unassigned = [c for c in components if id(c) not in assignments]
        farmers_un = [c for c in unassigned if c.role == "Farmer"]
        warriors_un = [c for c in unassigned if c.role == "Warrior"]

        # Keep min farmers for wheat
        min_farm = 1 if total <= 3 else 2
        farmers_for_farm = farmers_un[:min_farm]
        farmers_for_spawn = farmers_un[min_farm:]

        # Spawn pool: extra farmers + idle warriors (ssm >= 3 can't go to cave usefully)
        spawn_pool = list(farmers_for_spawn) + [c for c in warriors_un if c.steps_since_meal >= 3]

        # Decide spawning
        # Need spawn_cost + total for meal reserve
        if total < 5 and len(spawn_pool) >= 2:
            if num_w < 4 and wheat >= 12 + total:
                for i in range(min(2, len(spawn_pool) // 2)):
                    c1 = spawn_pool.pop(0)
                    c2 = spawn_pool.pop(0)
                    assignments[id(c1)] = "spawn warrior"
                    assignments[id(c2)] = "spawn warrior"
            elif wheat >= 10 + total:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                assignments[id(c1)] = "spawn farmer"
                assignments[id(c2)] = "spawn farmer"
        elif (num_w == 0 or w_in_cave < 2) and wheat >= 12 + total and len(spawn_pool) >= 2:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            assignments[id(c1)] = "spawn warrior"
            assignments[id(c2)] = "spawn warrior"
        elif num_w < 6 and w_in_cave < 3 and wheat >= 12 + total + 5 and len(spawn_pool) >= 2:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            assignments[id(c1)] = "spawn warrior"
            assignments[id(c2)] = "spawn warrior"

        # Phase 4: Assign remaining warriors
        # Those with ssm <= 2 go to cave, others farm
        for c in warriors_un:
            if id(c) not in assignments:
                if c.steps_since_meal <= 2:
                    assignments[id(c)] = "cave"
                else:
                    assignments[id(c)] = "farm"

        # Phase 5: Assign farmers
        for c in farmers_for_farm:
            if id(c) not in assignments:
                assignments[id(c)] = "farm"

        # Extra farmers: farm normally, go to cave only if wheat is abundant and dragon low
        wheat_surplus = wheat - total  # rough surplus after one meal per villager
        for c in spawn_pool:
            if id(c) not in assignments:
                if dragon_hp <= 15 and wheat_surplus >= 15:
                    assignments[id(c)] = "cave"
                else:
                    assignments[id(c)] = "farm"

        # Execute all assignments
        for c in components:
            if id(c) in assignments:
                environment.assign_group(c, assignments[id(c)])
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```