from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_farmers = [f for f in environment.farmers if f.hp > 0]
        all_warriors = [w for w in environment.warriors if w.hp > 0]
        total_villagers = len(all_farmers) + len(all_warriors)
        num_warriors_alive = len(all_warriors)
        num_farmers_in_village = len([f for f in environment.farmers if f.location == "Village" and f.hp > 0])
        num_warriors_in_village = len([w for w in environment.warriors if w.location == "Village" and w.hp > 0])

        # Step 1: Villagers that MUST eat (s_m >= 4 to be safe)
        eat_set = set()
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                eat_set.add(id(c))

        remaining = [c for c in components if id(c) not in eat_set]
        v_farmers = [c for c in remaining if c.role == "Farmer"]
        v_warriors = [c for c in remaining if c.role == "Warrior"]

        # Step 2: Decide on spawning
        # Reserve wheat: 1 meal per villager for safety
        wheat_reserve = total_villagers
        spawn_used = set()

        # Priority: spawn warriors if we need combat power
        need_warriors = (num_warriors_alive < 3 or total_villagers < 6)
        need_farmers = (len(all_farmers) < 2)

        # Try to spawn warriors using pairs of villagers in village
        spawn_pool = v_farmers  # prefer farmers as spawn parents

        if need_warriors and wheat >= 12 + wheat_reserve and len(spawn_pool) >= 2:
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            spawn_used = {id(spawn_pool[0]), id(spawn_pool[1])}
        elif need_warriors and wheat >= 12 + wheat_reserve and len(v_warriors) >= 2:
            # Fallback: use warriors as spawn parents
            environment.assign_group(v_warriors[0], "spawn warrior")
            environment.assign_group(v_warriors[1], "spawn warrior")
            spawn_used = {id(v_warriors[0]), id(v_warriors[1])}
        elif need_farmers and wheat >= 10 + wheat_reserve and len(spawn_pool) >= 2:
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            spawn_used = {id(spawn_pool[0]), id(spawn_pool[1])}

        v_farmers = [c for c in v_farmers if id(c) not in spawn_used]
        v_warriors = [c for c in v_warriors if id(c) not in spawn_used]

        # Step 3: Keep minimum farmers to produce wheat
        # 1 farmer produces 5w/step; each villager eats ~1w every 6 steps
        # So 1 farmer can sustain ~30 villagers. Keep 1-2 farming for buffer.
        min_farmers_farming = max(1, min(2, len(v_farmers)))

        for i, c in enumerate(v_farmers):
            if i < min_farmers_farming:
                environment.assign_group(c, "farm")
            elif num_warriors_alive <= 1 and c.steps_since_meal <= 2:
                # Emergency: send farmers to attack if very few warriors
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Step 4: Send warriors to cave (aggressive: s_m <= 2 gives 2+ attack steps)
        for c in v_warriors:
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                # Too hungry, farm briefly then eat and re-deploy
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Leave before starvation risk; arrive at village s_m=5, eat next
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")