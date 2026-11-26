

Looking at the failures, the win rate dropped because my spawning condition was too restrictive. The key issues:

1. `should_spawn` condition was too narrow - missing cases where `w_in_cave < 3` but `num_w >= 2`
2. Not spawning frequently enough means not enough warriors to overcome dragon's 5HP/step regen
3. Need 3+ warriors attacking every step (3×3-5=4 net damage/step, ~25 steps to kill 100HP)
4. Farmers should NEVER go to cave (they only do 1 damage and starve faster)

Strategy: Be extremely aggressive about spawning warriors. Keep only 1 farmer farming. Send all surplus to spawn pool. Warriors go to cave whenever ssm ≤ 2.

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

        assigned = {}  # id(c) -> group name

        # 1. Eat if ssm >= 5 (step 6 = starve)
        for c in components:
            if c.steps_since_meal >= 5:
                assigned[id(c)] = "eat"

        # 2. Warriors with ssm <= 1 go to cave immediately
        for c in components:
            if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 1:
                assigned[id(c)] = "cave"

        # 3. Spawning: always try to get warriors to the cave
        # Meal reserve: 1 wheat per villager to cover near-term meals
        reserve = total + 2

        # Build spawn pool from unassigned villagers (prioritize farmers since warriors should attack)
        unassigned = [c for c in components if id(c) not in assigned]
        un_farmers = [c for c in unassigned if c.role == "Farmer"]
        un_warriors = [c for c in unassigned if c.role == "Warrior"]

        # Keep at most 1 farmer farming (only if total >= 4, else keep 0 to spawn faster)
        min_farming = 1 if total >= 6 else 0
        # But always have at least 1 producing if very few villagers
        if total <= 3:
            min_farming = 1

        farming_farmers = un_farmers[:min_farming]
        excess_farmers = un_farmers[min_farming:]

        # Spawn pool: excess farmers + idle warriors (ssm >= 3, can't usefully go to cave)
        idle_warriors = [c for c in un_warriors if c.steps_since_meal >= 3]
        spawn_pool = excess_farmers + idle_warriors

        # Always try to spawn a warrior if possible
        if len(spawn_pool) >= 2 and wheat >= 12 + reserve:
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            assigned[id(spawn_pool[0])] = "spawn warrior"
            assigned[id(spawn_pool[1])] = "spawn warrior"
            spawn_pool = spawn_pool[2:]
        elif total < 5 and len(spawn_pool) >= 2 and wheat >= 10 + reserve:
            # Can't spawn warrior, grow economy with farmer
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            assigned[id(spawn_pool[0])] = "spawn farmer"
            assigned[id(spawn_pool[1])] = "spawn farmer"
            spawn_pool = spawn_pool[2:]

        # Second spawn attempt if we have enough
        if len(spawn_pool) >= 2 and wheat >= 24 + reserve:
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            assigned[id(spawn_pool[0])] = "spawn warrior"
            assigned[id(spawn_pool[1])] = "spawn warrior"
            spawn_pool = spawn_pool[2:]
        elif total < 4 and len(spawn_pool) >= 2 and wheat >= 20 + reserve:
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            assigned[id(spawn_pool[0])] = "spawn farmer"
            assigned[id(spawn_pool[1])] = "spawn farmer"
            spawn_pool = spawn_pool[2:]

        # 4. Warriors with ssm 2 go to cave (arrive ssm=3, attack once at ssm=4 then must leave - worth it for continuous coverage)
        for c in components:
            if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 2:
                assigned[id(c)] = "cave"

        # 5. Farming farmers
        for c in farming_farmers:
            if id(c) not in assigned:
                assigned[id(c)] = "farm"

        # 6. Remaining spawn pool members (not spawned) → farm
        for c in spawn_pool:
            if id(c) not in assigned:
                assigned[id(c)] = "farm"

        # 7. Idle warriors not in spawn pool (shouldn't happen, but safety)
        for c in un_warriors:
            if id(c) not in assigned:
                assigned[id(c)] = "farm"

        # Execute all assignments
        for c in components:
            if id(c) in assigned:
                environment.assign_group(c, assigned[id(c)])
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        # ssm >= 4: must go to village (travel 1 step → arrive ssm=5 → eat next step)
        # ssm <= 3: keep attacking
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```