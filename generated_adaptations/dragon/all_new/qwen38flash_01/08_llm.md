

Looking at the failures, the core issues are:

1. **Dragon never dies (0% win rate)**: Not enough warriors attacking, too conservative with spawning
2. **Not spawning aggressively enough**: When < 5 villagers with enough wheat, should spawn instead of farming
3. **No warriors → must spawn warriors urgently**

Key math: Dragon has 100 HP + 5 regen/step when unattacked. Need continuous attack coverage with 3+ warriors to win in ~25 steps. The warrior cycle is: Eat→Travel→Attack×3→Travel→Eat (6 steps, 3 attacks). Need 3 staggered warriors for continuous coverage.

Changes made:
- Much more aggressive spawning (always spawn when < 5 villagers with sufficient wheat)
- Priority warrior spawning when few/no warriors
- Simpler, cleaner assignment logic with proper tracking
- Warriors go to cave immediately after eating (ssm ≤ 1)
- Late game sends all farmers to cave

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

        def do_assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        # Priority 1: Eat if ssm >= 5 (starving at 6)
        for c in components:
            if c.steps_since_meal >= 5:
                do_assign(c, "eat")

        # Priority 2: Warriors with ssm <= 1 go to cave immediately
        for c in components:
            if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 1:
                do_assign(c, "cave")

        # Priority 3: Spawn warriors aggressively
        # Meal reserve = 1 wheat per villager
        meal_reserve = total
        unassigned_list = [c for c in components if id(c) not in assigned]

        # Always try to spawn warrior if we need more attackers
        should_spawn_warrior = False
        if len(unassigned_list) >= 2:
            if num_w == 0:
                # No warriors at all - critical, spawn one if possible
                if wheat >= 12 + meal_reserve:
                    should_spawn_warrior = True
            elif total < 5:
                # Under 5 villagers, aggressively build up
                if wheat >= 12 + meal_reserve:
                    should_spawn_warrior = True
            elif w_in_cave < 2 and wheat >= 12 + meal_reserve:
                # Need more attackers in cave
                should_spawn_warrior = True
            elif w_in_cave < 4 and wheat >= 22 + meal_reserve:
                # Build army while farming supports it
                should_spawn_warrior = True

        if should_spawn_warrior:
            # Prefer using farmers for spawning (they're less useful for attacking)
            farmers_un = [c for c in unassigned_list if c.role == "Farmer" and id(c) not in assigned]
            warriors_un = [c for c in unassigned_list if c.role == "Warrior" and id(c) not in assigned]

            pool = []
            # Use up to 2 farmers first, then warriors
            for f in farmers_un:
                if len(pool) < 2:
                    pool.append(f)
            for w in warriors_un:
                if len(pool) < 2:
                    pool.append(w)
            # If not enough from preferred, grab any unassigned
            if len(pool) < 2:
                for c in unassigned_list:
                    if id(c) not in assigned and id(c) not in [id(p) for p in pool]:
                        pool.append(c)
                    if len(pool) >= 2:
                        break

            if len(pool) >= 2:
                do_assign(pool[0], "spawn warrior")
                do_assign(pool[1], "spawn warrior")
                unassigned_list = [c for c in components if id(c) not in assigned]

        # Second spawn if still < 5 and affordable
        if total < 5 and len(unassigned_list) >= 2 and wheat >= 22 + meal_reserve:
            farmers_un2 = [c for c in unassigned_list if id(c) not in assigned]
            if len(farmers_un2) >= 2:
                do_assign(farmers_un2[0], "spawn warrior")
                do_assign(farmers_un2[1], "spawn warrior")
                unassigned_list = [c for c in components if id(c) not in assigned]

        # Priority 4: Spawn farmer if < 5 villagers and have 2+ farmers
        if total < 5:
            farmers_avail = [c for c in components if id(c) not in assigned and c.role == "Farmer"]
            if len(farmers_avail) >= 2 and wheat >= 10 + meal_reserve:
                # But keep at least 1 for farming if total >= 3
                if total >= 4 or len([c for c in components if id(c) not in assigned and c.role == "Farmer"]) <= 3:
                    do_assign(farmers_avail[0], "spawn farmer")
                    do_assign(farmers_avail[1], "spawn farmer")

        # Priority 5: Remaining warriors go to cave or farm
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                if c