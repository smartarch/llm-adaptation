from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_v = list(environment.warriors) + list(environment.farmers)
        num_w = len(environment.warriors)
        num_f = len(environment.farmers)
        assigned = set()

        # PHASE 1: Mandatory eat - villagers in village with s_m >= 4 must eat
        # (if s_m=4 and they don't eat, next step s_m=5, then step after s_m=6 = starving)
        eat_set = set()
        for c in components:
            if c.steps_since_meal >= 4 and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
                eat_set.add(id(c))
                assigned.add(id(c))

        # PHASE 2: Compute meals due next step (wheat reservation)
        # Villagers in village with s_m=3 (not eating) → s_m=4 next step, must eat next step
        # Villagers in cave with s_m=4 → leave cave, arrive village s_m=5, must eat next step
        # Village villagers in eat_set will reset to s_m=0, won't need next step
        meals_next = 0
        for v in all_v:
            if v.location == "Village":
                if id(v) not in eat_set and v.steps_since_meal >= 3:
                    meals_next += 1
            elif v.location == "Cave":
                # Will leave at s_m>=4, arrive village at s_m+1>=5, must eat
                if v.steps_since_meal >= 4:
                    meals_next += 1
        # Also: villagers in village with s_m>=4 who couldn't eat (no wheat) will starve
        for c in components:
            if c.steps_since_meal >= 4 and id(c) not in eat_set:
                meals_next += 1  # will desperately need wheat

        # PHASE 3: Try to spawn a warrior using 2 villagers (parents not consumed)
        non_assigned = [c for c in components if id(c) not in assigned]
        non_assigned.sort(key=lambda c: 0 if c.role == "Farmer" else 1)

        spawn_set = set()
        if len(non_assigned) >= 2 and wheat >= 12:
            # Estimate farm income this step: non-spawn farmers will mostly farm
            potential_farmers = [c for c in non_assigned[2:] if c.role == "Farmer"]
            est_income = 5 * len(potential_farmers) + 2  # generous estimate
            # Allow spawn if (wheat - 12 + est_income) >= meals_next
            if wheat - 12 + est_income >= meals_next or num_w == 0:
                environment.assign_group(non_assigned[0], "spawn warrior")
                environment.assign_group(non_assigned[1], "spawn warrior")
                wheat -= 12
                spawn_set = {id(non_assigned[0]), id(non_assigned[1])}
                assigned.add(id(non_assigned[0]))
                assigned.add(id(non_assigned[1]))

        # PHASE 4: Assign remaining villagers
        remaining = [c for c in components if id(c) not in assigned]
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # Count current cave occupants (attackers)
        cave_count = sum(1 for v in all_v if v.location == "Cave")

        # Farmers: keep some farming for wheat, send extras to cave if attackers scarce
        for i, c in enumerate(farmers_rem):
            if c.steps_since_meal >= 4:
                # Already handled in phase 1 if wheat available; if not, farm and accept risk
                environment.assign_group(c, "farm")
            elif i < 1 or (i < 2 and num_w >= 4 and cave_count >= 2):
                environment.assign_group(c, "farm")
            elif c.steps_since_meal <= 2 and (num_w <= 2 or cave_count <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(id(c))

        # Warriors: send to cave aggressively when fresh enough for 2+ attack steps
        for c in warriors_rem:
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            elif num_w <= 2 and c.steps_since_meal <= 3:
                environment.assign_group(c, "cave")
            else:
                # Stay in village, eat soon, then redeploy
                environment.assign_group(c, "farm")
            assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Travel to village (1 step), arrive s_m=5, eat next step to reset.
                # Avoids s_m=6 starvation.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")