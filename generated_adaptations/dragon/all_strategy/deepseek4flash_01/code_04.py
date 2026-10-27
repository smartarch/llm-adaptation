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
                # Keep only components that were seen during the previous step.
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

        # Mandatory meals first. A villager with 5 missed meals must eat now.
        mandatory = [c for c in comps if c.steps_since_meal >= 5]
        eaters = list(mandatory)
        available_meals = max(0, wheat - len(eaters))

        # Warriors that just returned from the Cave should eat early if possible.
        early_warriors = [
            c for c in comps
            if c.role == "Warrior" and c.steps_since_meal == 4
        ]
        early_warriors.sort(key=lambda c: c.hp, reverse=True)
        for c in early_warriors:
            if available_meals <= 0:
                break
            eaters.append(c)
            available_meals -= 1

        # Farmers can also eat at 4, but only if there is clear surplus.
        early_farmers = [
            c for c in comps
            if c.role == "Farmer" and c.steps_since_meal == 4
        ]
        early_farmers.sort(key=lambda c: c.hp, reverse=True)
        for c in early_farmers:
            if available_meals <= 2:
                break
            eaters.append(c)
            available_meals -= 1

        eater_ids = {id(c) for c in eaters}
        remaining_wheat = wheat - len(eaters)

        spawn_pool = [c for c in comps if id(c) not in eater_ids]
        # Prefer using farmers as spawners so warriors can go to the Cave.
        spawn_pool.sort(key=lambda c: (c.role != "Farmer", c.steps_since_meal))

        soon_hungry = sum(1 for c in comps if c.steps_since_meal >= 3)
        reserve = 2 + min(4, soon_hungry + self._cave_soon_hungry)

        spawn_ids = set()
        spawn_group = None
        spawned_this_step = False

        def do_spawn(group, cost, allow_low_reserve=False):
            nonlocal remaining_wheat, spawn_group, spawned_this_step
            if spawned_this_step or len(spawn_pool) < 2:
                return False
            if remaining_wheat < cost:
                return False
            if not allow_low_reserve and remaining_wheat - cost < reserve:
                return False

            for c in spawn_pool[:2]:
                spawn_ids.add(id(c))

            remaining_wheat -= cost
            spawned_this_step = True
            spawn_group = group

            if group == "spawn warrior":
                self._spawned_warriors += 1
            else:
                self._spawned_farmers += 1
            return True

        # First priority: get at least one warrior into the Cave early.
        if total_warriors == 0:
            do_spawn(
                "spawn warrior",
                12,
                allow_low_reserve=(len(mandatory) == 0),
            )

        # If the economy is tiny, add a farmer before more warriors.
        if not spawned_this_step and total_farmers < 2:
            do_spawn("spawn farmer", 10)

        # Maintain a reasonable warrior count for continuous attacks.
        if not spawned_this_step and total_warriors < 4 and step <= 24:
            do_spawn("spawn warrior", 12)

        # Make sure farmers are spawned when safe.
        if (
            not spawned_this_step
            and total_farmers < 4
            and self._spawned_farmers < 2
            and step <= 20
        ):
            do_spawn("spawn farmer", 10)

        # Extra warriors are useful if the economy can support them.
        if (
            not spawned_this_step
            and total_warriors < 5
            and step <= 18
        ):
            do_spawn("spawn warrior", 12)

        for c in comps:
            if id(c) in eater_ids:
                environment.assign_group(c, "eat")

        for c in comps:
            if id(c) in spawn_ids:
                environment.assign_group(c, spawn_group)

        for c in comps:
            if id(c) in eater_ids or id(c) in spawn_ids:
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
            # Do not let a warrior reach 5 missed meals while still in the Cave.
            high = [c for c in warriors if c.steps_since_meal >= 4]
            mid = [c for c in warriors if c.steps_since_meal == 3]
            low = [c for c in warriors if c.steps_since_meal <= 2]

            for c in high:
                return_ids.add(id(c))

            # If nobody is fresh, keep only one mid-hunger warrior attacking
            # and send the others home to eat. This staggers meal breaks.
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