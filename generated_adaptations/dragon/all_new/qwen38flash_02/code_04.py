import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)
        total_villagers = total_warriors + total_farmers

        # Separate into urgent (must eat) and available
        must_eat = []
        avail = []
        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            else:
                avail.append(c)

        # Urgent eaters eat now
        for c in must_eat:
            environment.assign_group(c, "eat")

        avail_warriors = [c for c in avail if c.role == "Warrior"]
        avail_farmers = [c for c in avail if c.role == "Farmer"]

        # Decide spawning: use pairs of farmers
        # Keep at least 1 farmer farming if possible
        farmers_pool = list(avail_farmers)
        n_for_other = 0  # farmers consumed for spawning

        if len(farmers_pool) >= 2:
            # Priority: if no warriors at all, spawn warrior immediately
            if total_warriors == 0 and wheat >= 12:
                environment.assign_group(farmers_pool[0], "spawn warrior")
                environment.assign_group(farmers_pool[1], "spawn warrior")
                n_for_other = 2
            elif total_warriors < 5 and wheat >= 12:
                # Keep growing warrior army up to 5
                environment.assign_group(farmers_pool[0], "spawn warrior")
                environment.assign_group(farmers_pool[1], "spawn warrior")
                n_for_other = 2
            elif total_villagers < 6 and wheat >= 10:
                # Need more total villagers: spawn farmer if we have enough warriors
                if total_warriors >= 4 and wheat >= 10:
                    environment.assign_group(farmers_pool[0], "spawn farmer")
                    environment.assign_group(farmers_pool[1], "spawn farmer")
                    n_for_other = 2
                elif wheat >= 12:
                    environment.assign_group(farmers_pool[0], "spawn warrior")
                    environment.assign_group(farmers_pool[1], "spawn warrior")
                    n_for_other = 2
                elif wheat >= 10:
                    environment.assign_group(farmers_pool[0], "spawn farmer")
                    environment.assign_group(farmers_pool[1], "spawn farmer")
                    n_for_other = 2

        # ALL available warriors go to cave (aggressive!)
        for w in avail_warriors:
            if w.hp >= 1:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # Remaining farmers farm
        for f in farmers_pool[n_for_other:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Must return to village to eat before starving
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                # Too fragile, retreat to village
                environment.assign_group(c, "village")
            else:
                # Attack the dragon every step
                environment.assign_group(c, "attack")