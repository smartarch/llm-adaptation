from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._first_attack_step = None
        self._last_attack_step = None
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        comps = list(components)
        wheat = environment.farm.wheat

        # Decide who should eat. Warriors eat a bit earlier so they can
        # return to the Cave and attack instead of being forced back soon.
        desired_eaters = []
        for c in comps:
            if c.steps_since_meal >= 5:
                desired_eaters.append(c)
            elif c.role == "Warrior" and c.steps_since_meal >= 3:
                desired_eaters.append(c)

        desired_eaters.sort(
            key=lambda c: (c.steps_since_meal, c.role == "Warrior"),
            reverse=True
        )

        num_eat = min(len(desired_eaters), max(0, wheat))
        eaters = desired_eaters[:num_eat]
        eater_ids = {id(c) for c in eaters}
        remaining_wheat = wheat - num_eat

        spawn_pool = [
            c for c in comps
            if c.role == "Farmer" and id(c) not in eater_ids
        ]
        spawn_pool.sort(key=lambda c: c.steps_since_meal)

        spawn_farmer_ids = set()
        spawn_warrior_ids = set()

        def take_for_spawn(target_ids, cost, max_pairs):
            nonlocal remaining_wheat
            available = [
                c for c in spawn_pool
                if id(c) not in spawn_farmer_ids
                and id(c) not in spawn_warrior_ids
            ]
            pairs = min(max_pairs, len(available) // 2, remaining_wheat // cost)
            if pairs <= 0:
                return 0
            for c in available[:2 * pairs]:
                target_ids.add(id(c))
            remaining_wheat -= pairs * cost
            return pairs

        # Keep some wheat for upcoming meals after the first attack.
        if self._first_attack_step is None:
            reserve = 0
        else:
            reserve = max(2, len(comps) // 2)

        # Spawn order: first warrior, first farmer, second warrior, second farmer.
        if self._spawned_warriors == 0 and remaining_wheat - 12 >= reserve:
            self._spawned_warriors += take_for_spawn(
                spawn_warrior_ids, 12, 1
            )

        if self._spawned_farmers == 0 and remaining_wheat - 10 >= reserve:
            self._spawned_farmers += take_for_spawn(
                spawn_farmer_ids, 10, 1
            )

        if self._spawned_warriors < 2 and remaining_wheat - 12 >= reserve:
            self._spawned_warriors += take_for_spawn(
                spawn_warrior_ids, 12, 2 - self._spawned_warriors
            )

        if self._spawned_farmers < 2 and remaining_wheat - 10 >= reserve:
            self._spawned_farmers += take_for_spawn(
                spawn_farmer_ids, 10, 2 - self._spawned_farmers
            )

        # After satisfying minimum spawns, add extra warriors if the economy allows.
        if (
            self._spawned_warriors >= 2
            and self._spawned_farmers >= 2
            and self._spawned_warriors < 4
            and step <= 20
            and remaining_wheat - 12 >= reserve + 2
        ):
            self._spawned_warriors += take_for_spawn(
                spawn_warrior_ids, 12, 1
            )

        # Assign in priority order so eating and spawning are clear.
        for c in comps:
            if id(c) in eater_ids:
                environment.assign_group(c, "eat")

        for c in comps:
            if id(c) in spawn_warrior_ids:
                environment.assign_group(c, "spawn warrior")

        for c in comps:
            if id(c) in spawn_farmer_ids:
                environment.assign_group(c, "spawn farmer")

        for c in comps:
            if (
                id(c) in eater_ids
                or id(c) in spawn_warrior_ids
                or id(c) in spawn_farmer_ids
            ):
                continue

            if c.role == "Warrior":
                # If there is no wheat and the warrior is in danger of starving,
                # use this step to farm and produce food for the next step.
                if c.steps_since_meal >= 5 and remaining_wheat <= 0:
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        comps = list(components)
        if not comps:
            return

        # Farmers should not fight in the Cave.
        return_ids = {id(c) for c in comps if c.role == "Farmer"}
        warriors = [c for c in comps if c.role == "Warrior"]

        urgent = [c for c in warriors if c.steps_since_meal >= 5]
        moderate = [c for c in warriors if c.steps_since_meal == 4]
        fresh = [c for c in warriors if c.steps_since_meal < 4]

        # Urgent warriors must return to eat.
        for c in urgent:
            return_ids.add(id(c))

        # Rotate moderate warriors so meals are staggered.
        if moderate:
            if fresh:
                if len(moderate) > 1:
                    keep = max(moderate, key=lambda c: c.hp)
                    for c in moderate:
                        if c is not keep:
                            return_ids.add(id(c))
                else:
                    return_ids.add(id(moderate[0]))
            else:
                if len(moderate) > 1:
                    keep = max(moderate, key=lambda c: c.hp)
                    for c in moderate:
                        if c is not keep:
                            return_ids.add(id(c))
                # If there is only one moderate warrior, keep it attacking
                # this step and let it return next step.
        else:
            # No fresh or moderate warrior: try to keep one urgent warrior
            # attacking if it can still deal damage this step.
            if not fresh:
                candidates = [
                    c for c in urgent
                    if c.steps_since_meal <= 5
                ]
                if len(urgent) > 1 and candidates:
                    keep = min(
                        candidates,
                        key=lambda c: (c.steps_since_meal, -c.hp)
                    )
                    return_ids.discard(id(keep))

        attacking = []
        for c in comps:
            if id(c) in return_ids:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
                attacking.append(c)

        if attacking:
            if self._first_attack_step is None:
                self._first_attack_step = step
            self._last_attack_step = step