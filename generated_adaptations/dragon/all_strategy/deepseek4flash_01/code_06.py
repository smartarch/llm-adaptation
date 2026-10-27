from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_step = None
        self._seen_ids = set()
        self._alive_roles = {}
        self._cave_soon_hungry = 0
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._last_attack_step = None

    def _begin_step(self, step, components):
        if self._current_step != step:
            if self._current_step is not None:
                self._alive_roles = {
                    cid: role
                    for cid, role in self._alive_roles.items()
                    if cid in self._seen_ids
                }
            self._current_step = step
            self._seen_ids = set()

        for c in components:
            self._seen_ids.add(id(c))
            self._alive_roles[id(c)] = c.role

    def assign_in_village(self, components, environment, group_ids, step):
        comps = list(components)
        self._begin_step(step, comps)

        wheat = environment.farm.wheat
        total_warriors = sum(
            1 for role in self._alive_roles.values() if role == "Warrior"
        )
        total_farmers = sum(
            1 for role in self._alive_roles.values() if role == "Farmer"
        )

        remaining_wheat = wheat
        eater_ids = set()

        # Mandatory meals first: a villager at 5 missed meals must eat now.
        mandatory = [c for c in comps if c.steps_since_meal >= 5]
        mandatory.sort(key=lambda c: c.steps_since_meal, reverse=True)
        for c in mandatory:
            if remaining_wheat > 0:
                eater_ids.add(id(c))
                remaining_wheat -= 1

        # Warriors that just returned from the Cave should eat as early as possible.
        early_warriors = [
            c for c in comps
            if c.role == "Warrior"
            and c.steps_since_meal >= 4
            and id(c) not in eater_ids
        ]
        early_warriors.sort(key=lambda c: c.hp, reverse=True)
        for c in early_warriors:
            if remaining_wheat > 0:
                eater_ids.add(id(c))
                remaining_wheat -= 1

        # Farmers eat at 4 only when there is a clear surplus.
        early_farmers = [
            c for c in comps
            if c.role == "Farmer"
            and c.steps_since_meal >= 4
            and id(c) not in eater_ids
        ]
        early_farmers.sort(key=lambda c: c.hp, reverse=True)
        for c in early_farmers:
            if remaining_wheat > 2:
                eater_ids.add(id(c))
                remaining_wheat -= 1

        available = [c for c in comps if id(c) not in eater_ids]
        # Prefer farmers as spawners so warriors can go to the Cave.
        available.sort(key=lambda c: (c.role != "Farmer", c.steps_since_meal))

        spawn_assign = {}
        # Reserve for warriors that will return from the Cave and need food soon.
        reserve = max(2, self._cave_soon_hungry + 1)

        def spawn_group(group, max_spawns, cost, local_reserve):
            nonlocal remaining_wheat
            if max_spawns <= 0:
                return 0

            max_possible = min(max_spawns, len(available) // 2)
            if max_possible <= 0:
                return 0

            max_afford = max(0, (remaining_wheat - local_reserve) // cost)
            k = min(max_possible, max_afford)
            if k <= 0:
                return 0

            selected = available[: 2 * k]
            del available[: 2 * k]
            for c in selected:
                spawn_assign[id(c)] = group

            remaining_wheat -= k * cost
            if group == "spawn warrior":
                self._spawned_warriors += k
            else:
                self._spawned_farmers += k
            return k

        # Earliest possible warrior for an early first attack.
        if total_warriors == 0:
            spawn_group("spawn warrior", 1, 12, 0)

        # Keep at least a small farmer base.
        if total_farmers < 2:
            spawn_group("spawn farmer", 1, 10, reserve)

        # Main warrior build-up. Multiple pairs may be spawned in one step.
        target_warriors = 7
        if step <= 20:
            spawn_group(
                "spawn warrior",
                target_warriors - total_warriors,
                12,
                reserve,
            )

        # Ensure the farmer requirement is satisfied if wheat permits.
        if total_farmers < 2:
            spawn_group("spawn farmer", 1, 10, reserve)

        if total_farmers < 3 and step <= 15:
            spawn_group("spawn farmer", 1, 10, reserve)

        # A small amount of extra warrior production late in the build-up.
        if step <= 18:
            spawn_group("spawn warrior", 2, 12, reserve)

        for c in comps:
            if id(c) in eater_ids:
                environment.assign_group(c, "eat")

        for c in comps:
            if id(c) in spawn_assign:
                environment.assign_group(c, spawn_assign[id(c)])

        for c in comps:
            if id(c) in eater_ids or id(c) in spawn_assign:
                continue

            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        comps = list(components)
        self._begin_step(step, comps)

        if not comps:
            self._cave_soon_hungry = 0
            return

        return_ids = {id(c) for c in comps if c.role == "Farmer"}
        warriors = [c for c in comps if c.role == "Warrior"]

        if warriors:
            # A warrior at 4 missed meals must leave the Cave now so they can
            # eat in the Village before reaching 5.
            high = [c for c in warriors if c.steps_since_meal >= 4]
            mid = [c for c in warriors if c.steps_since_meal == 3]
            low = [c for c in warriors if c.steps_since_meal <= 2]

            for c in high:
                return_ids.add(id(c))

            # Stagger mid-hunger warriors when possible so that the Dragon
            # is not left unattacked while everyone is eating.
            if not low and mid:
                keep = max(mid, key=lambda c: c.hp)
                for c in mid:
                    if c is not keep:
                        return_ids.add(id(c))

        attacking = []
        for c in comps:
            if id(c) in return_ids:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
                attacking.append(c)

        if attacking:
            self._last_attack_step = step

        self._cave_soon_hungry = sum(
            1 for c in attacking if c.steps_since_meal >= 3
        )