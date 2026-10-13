

The strategy is to split the economy and the army cleanly:

1. Warriors are treated as the attack force. Every warrior seen in the Village is sent to the Cave. Every warrior seen in the Cave is assigned to attack. This keeps the maximum possible damage output on the Dragon and satisfies the requirement that all warriors should be in the Cave attacking.

2. Farmers are treated as the economic base. Every farmer seen in the Cave is sent back to the Village. Every farmer seen in the Village is assigned either to farming, to spawning new farmers, or to spawning new warriors. No farmer is allowed to join the cave fight, because the requirements explicitly say that farmers should remain in the Village.

3. Wheat is used to grow both populations. The strategy uses a target army size of 10 warriors while the Dragon is healthy, and a target Village population of 10 farmers. If the Dragon is almost dead, or if the 30-step limit is close, the target warrior count is reduced to 4 because a smaller force is enough and fewer villagers are wasted near the end.

4. The strategy always tries to produce at least a few farmers and at least a few warriors. It keeps internal counters of approximate farmer-spawning and warrior-spawning attempts. If fewer than two spawn-pairs of either type have been created yet, it will try to make them when wheat and surplus villagers are available.

5. To avoid starving the economy, the strategy normally reserves at least two farmers to farm each step. It breaks this reservation only when the attack force is critically weak, for example when there are no warriors available or when there are fewer than six warriors and there is still enough time to recover.

6. When there are not enough villagers to spawn both a farmer and a warrior in the same step, the strategy prefers early warrior spawns when there is no attack force. If there is already some attack force and the farmer count is still too low, it may prefer an early farmer spawn to stabilize the wheat economy.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    TARGET_WARRIORS = 10
    TARGET_FARMERS = 10
    MIN_SPAWN_WARRIORS = 2
    MIN_SPAWN_FARMERS = 2
    FARM_RESERVE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.cave_warriors = 0

    def _get_int(self, obj, attr, default=0):
        try:
            value = getattr(obj, attr, default)
            if value is None:
                return default
            return int(value)
        except Exception:
            return default

    def _is_warrior(self, component):
        return str(getattr(component, "role", "")).strip().lower() == "warrior"

    def _assign_pairs(
        self,
        environment,
        villagers,
        start,
        group_name,
        cost,
        pairs,
        wheat_left,
        min_remaining,
    ):
        idx = start
        assigned = 0

        while (
            pairs > 0
            and idx + 1 < len(villagers)
            and wheat_left >= cost
            and len(villagers) - (idx + 2) >= min_remaining
        ):
            environment.assign_group(villagers[idx], group_name)
            environment.assign_group(villagers[idx + 1], group_name)

            idx += 2
            wheat_left -= cost
            pairs -= 1
            assigned += 1

        return idx, wheat_left, assigned

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components or [])

        warriors = []
        farmers = []

        for component in components:
            if self._is_warrior(component):
                warriors.append(component)
            else:
                farmers.append(component)

        # All warriors belong in the Cave as quickly as possible.
        for warrior in warriors:
            environment.assign_group(warrior, "cave")

        if not farmers:
            return

        dragon_hp = self._get_int(getattr(environment, "dragon", None), "hp", 50)
        if dragon_hp <= 0:
            for farmer in farmers:
                environment.assign_group(farmer, "farm")
            return

        wheat_left = self._get_int(getattr(environment, "farm", None), "wheat", 0)

        current_warriors = len(warriors) + self.cave_warriors
        no_warriors = current_warriors == 0
        warrior_emergency = current_warriors <= 1 or (current_warriors < 6 and step <= 25)

        if dragon_hp <= 15:
            target_warriors = 4
        elif step > 22:
            target_warriors = 4
        else:
            target_warriors = self.TARGET_WARRIORS

        force_w = self.spawned_warriors < self.MIN_SPAWN_WARRIORS
        force_f = self.spawned_farmers < self.MIN_SPAWN_FARMERS

        # If there is already at least one warrior but no farmers have been
        # spawned yet, and there are only a few farmers left, it can be worth
        # using a pair to stabilize the farmer population instead of always
        # sending every farmer pair to spawn warriors.
        prefer_early_farmer = False
        if force_f and len(farmers) <= 3 and current_warriors > 0:
            if len(farmers) == 2 and wheat_left >= self.FARMER_SPAWN_COST + 10:
                prefer_early_farmer = True
            elif len(farmers) == 3 and wheat_left >= self.FARMER_SPAWN_COST + 5:
                prefer_early_farmer = True

            if prefer_early_farmer:
                prefer_early_farmer = self.spawned_warriors >= self.spawned_farmers + 1

        # Decide how many farmer pairs may be spent on spawning warriors.
        # Normally keep two farmers farming. In an emergency, allow all or
        # nearly all farmers to produce warriors because otherwise there is no
        # meaningful way to kill the Dragon.
        if no_warriors:
            min_remaining_w = 0
            reserve_w = 0
        elif prefer_early_farmer or (warrior_emergency or force_w):
            min_remaining_w = (
                self.FARM_RESERVE if len(farmers) >= 2 * self.FARM_RESERVE else 0
            )
            reserve_w = min_remaining_w
        else:
            min_remaining_w = self.FARM_RESERVE
            reserve_w = self.FARM_RESERVE

        max_w_pairs = max(0, (len(farmers) - reserve_w) // 2)
        desired_w = 0

        if not prefer_early_farmer:
            if force_w and len(farmers) >= 2:
                desired_w = max(desired_w, 1)

            if warrior_emergency and len(farmers) >= 2:
                desired_w = max(desired_w, 1)

            needed_w = max(0, target_warriors - current_warriors)
            if needed_w > 0 and len(farmers) >= 4:
                desired_w = max(desired_w, min(max_w_pairs, needed_w))

        cap_w = 4 if no_warriors else 2
        desired_w = min(desired_w, cap_w, max_w_pairs)

        idx, wheat_left, w_assigned = self._assign_pairs(
            environment,
            farmers,
            0,
            "spawn warrior",
            self.WARRIOR_SPAWN_COST,
            desired_w,
            wheat_left,
            min_remaining_w,
        )
        self.spawned_warriors += w_assigned

        remaining = len(farmers) - idx
        desired_f = 0

        # Spawn farmers when the farmer population is too small or when the
        # minimum number of farmer spawns has not yet been reached.
        if force_f:
            if remaining >= 2:
                if remaining == 2:
                    if wheat_left >= self.FARMER_SPAWN_COST + 10:
                        desired_f = 1
                elif remaining == 3:
                    if wheat_left >= self.FARMER_SPAWN_COST + 5:
                        desired_f = 1
                else:
                    desired_f = 1
        else:
            farmer_count_now = len(farmers)

            if (
                remaining >= 2 * self.FARM_RESERVE
                and farmer_count_now < self.TARGET_FARMERS
            ):
                desired_f = 1

            if (
                remaining >= 3 * self.FARM_RESERVE
                and wheat_left >= 30
                and farmer_count_now < self.TARGET_FARMERS
            ):
                desired_f = 2

        if force_f:
            if remaining >= 4:
                min_remaining_f = self.FARM_RESERVE
            elif remaining == 3:
                min_remaining_f = 1
            else:
                min_remaining_f = 0
        else:
            min_remaining_f = self.FARM_RESERVE

        max_f_pairs = max(0, (remaining - min_remaining_f) // 2)
        desired_f = min(desired_f, 2, max_f_pairs)

        if desired_f > 0 and wheat_left >= self.FARMER_SPAWN_COST:
            idx, wheat_left, f_assigned = self._assign_pairs(
                environment,
                farmers,
                idx,
                "spawn farmer",
                self.FARMER_SPAWN_COST,
                desired_f,
                wheat_left,
                min_remaining_f,
            )
            self.spawned_farmers += f_assigned

        # Every farmer that was not used for spawning farms.
        for farmer in farmers[idx:]:
            environment.assign_group(farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        components = list(components or [])

        if not components:
            self.cave_warriors = 0
            return

        warriors = []
        non_warriors = []

        for component in components:
            if self._is_warrior(component):
                warriors.append(component)
            else:
                non_warriors.append(component)

        self.cave_warriors = len(warriors)

        # All warriors in the Cave attack immediately.
        for warrior in warriors:
            environment.assign_group(warrior, "attack")

        # Farmers must not stay in the Cave; they return to the Village.
        for farmer in non_warriors:
            environment.assign_group(farmer, "village")
```