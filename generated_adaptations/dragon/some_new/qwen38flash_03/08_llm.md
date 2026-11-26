

Looking at the seed=3 failure, the issue is that unlucky dragon counter-attacks kill warriors, creating gaps where the dragon regens 5 HP/step. The strategy needs:

1. **Aggressive warrior spawning** throughout the game, not just early
2. **Emergency attack coverage** - when warriors are scarce, send farmers to prevent regen
3. **More warriors deployed faster** - don't hold warriors in village unnecessarily
4. **Lower wheat threshold for spawning** - prioritize getting combat power up
5. **When very few warriors exist, sacrifice farming** to send more attackers

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_w = list(environment.warriors)
        all_f = list(environment.farmers)
        total_villagers = len(all_w) + len(all_f)
        num_w = len(all_w)
        num_f = len(all_f)

        # 1) Must eat: s_m >= 4 to avoid HP loss on travel
        eat_set = set()
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                eat_set.add(id(c))

        remaining = [c for c in components if id(c) not in eat_set]
        v_f = [c for c in remaining if c.role == "Farmer"]
        v_w = [c for c in remaining if c.role == "Warrior"]

        # 2) Spawning - very aggressive to build warrior army
        spawn_ids = set()
        reserve = total_villagers  # 1 meal per villager buffer

        # Pool of potential spawn parents (farmers in village, keeping 1 to farm)
        # If we need warriors badly, we can use more farmers as parents
        need_warriors = (num_w < 4 or total_villagers < 6)
        need_farmers = (num_f < 2)

        # Available farmer parents for spawning
        min_farmers_farming = 1 if num_f >= 2 else 0
        parent_candidates = v_f[min_farmers_farming:]

        if len(parent_candidates) >= 2 and wheat >= 12 + reserve and need_warriors:
            environment.assign_group(parent_candidates[0], "spawn warrior")
            environment.assign_group(parent_candidates[1], "spawn warrior")
            spawn_ids = {id(parent_candidates[0]), id(parent_candidates[1])}
        elif need_warriors and wheat >= 12 and len(v_w) >= 2:
            # No spare farmers, use warriors as parents (they aren't consumed)
            environment.assign_group(v_w[0], "spawn warrior")
            environment.assign_group(v_w[1], "spawn warrior")
            spawn_ids = {id(v_w[0]), id(v_w[1])}
        elif len(parent_candidates) >= 2 and wheat >= 10 + reserve and need_farmers:
            environment.assign_group(parent_candidates[0], "spawn farmer")
            environment.assign_group(parent_candidates[1], "spawn farmer")
            spawn_ids = {id(parent_candidates[0]), id(parent_candidates[1])}

        v_f = [c for c in v_f if id(c) not in spawn_ids]
        v_w = [c for c in v_w if id(c) not in spawn_ids]

        # 3) Count current cave attackers to decide reinforcements
        cave_attackers = sum(
            1 for v in all_w + all_f
            if v.location == "Cave" and v.steps_since_meal < 4
        )

        # 4) Farmers: farm, but send extras to cave if attack coverage is weak
        for i, c in enumerate(v_f):
            if i < min_farmers_farming:
                environment.assign_group(c, "farm")
            elif cave_attackers < 2 and c.steps_since_meal <= 2:
                # Emergency: send farmers to attack to prevent regen
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # 5) Warriors: send to cave aggressively
        for c in v_w:
            if c.steps_since_meal <= 1:
                # Best efficiency: arrive s_m<=2, attack 2-3 steps
                environment.assign_group(c, "cave")
            elif c.steps_since_meal <= 3 and cave_attackers < 2:
                # Urgent: even a single attack prevents 5HP regen
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c