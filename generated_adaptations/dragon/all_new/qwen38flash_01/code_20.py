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

        result = {}  # id(c) -> group name, never overwritten

        # Phase 1: Must eat (ssm >= 5; at step ssm=6 they starve)
        for c in components:
            if c.steps_since_meal >= 5:
                result[id(c)] = "eat"

        # Phase 2: Warriors with ssm <= 1 go to cave (just ate or very fresh)
        for c in components:
            if id(c) not in result and c.role == "Warrior" and c.steps_since_meal <= 1:
                result[id(c)] = "cave"

        # Phase 3: Spawn decisions
        # Remaining unassigned, split by role
        un = [c for c in components if id(c) not in result]
        un_f = [c for c in un if c.role == "Farmer"]
        un_w = [c for c in un if c.role == "Warrior"]

        # Keep min farmers producing wheat (1 when small, 2 when we have a bigger base)
        min_f = 1 if total <= 3 else 2
        farm_keep = un_f[:min_f]
        excess_f = un_f[min_f:]

        # Spawn pool: excess farmers + idle warriors (ssm >= 3 can't usefully go to cave)
        idle_w = [c for c in un_w if c.steps_since_meal >= 3]
        sp = excess_f + idle_w

        # "Enough wheat" test criterion: cost + total (1 meal per villager reserve)
        can_spawn_farmer = (total < 5) and (wheat >= 10 + total) and (len(sp) >= 2)
        can_spawn_warrior = (total < 5 or num_w < 3 or w_in_cave < 2) and (wheat >= 12 + total) and (len(sp) >= 2)

        if can_spawn_warrior:
            result[id(sp[0])] = "spawn warrior"
            result[id(sp[1])] = "spawn warrior"
            sp = sp[2:]
        elif can_spawn_farmer:
            result[id(sp[0])] = "spawn farmer"
            result[id(sp[1])] = "spawn farmer"
            sp = sp[2:]

        # Phase 4: Remaining warriors with ssm <= 2 → cave (still useful for coverage)
        for c in un_w:
            if id(c) not in result and c.steps_since_meal <= 2:
                result[id(c)] = "cave"

        # Phase 5: Farmers stay in village (they're bad attackers, 1 dmg)
        for c in farm_keep:
            if id(c) not in result:
                result[id(c)] = "farm"
        for c in sp:
            if id(c) not in result:
                result[id(c)] = "farm"

        # Safety: anything not assigned → farm
        for c in components:
            if id(c) not in result:
                result[id(c)] = "farm"
            environment.assign_group(c, result[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        # ssm >= 4: MUST go to village (travel 1 step → arrive ssm=5 → eat next step)
        # ssm <= 3: keep attacking to prevent dragon's 5HP/step regen
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")