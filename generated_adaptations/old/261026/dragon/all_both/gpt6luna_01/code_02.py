from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Count successful spawn assignments; each requires a pair and enough wheat.
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        assignments = [(c, "cave") for c in components if c.role == "Warrior"]

        # Farmers not used for spawning stay in the Village and farm.
        remaining = list(farmers)
        wheat = environment.farm.wheat

        def spawn_pair(group, cost):
            """Assign two farmers to a spawn group if wheat and farmers permit."""
            nonlocal wheat, remaining
            if wheat < cost or len(remaining) < 2:
                return False

            # Normally keep at least one farmer farming. If only two farmers
            # are available, allow one needed spawn to use both.
            has_unmet_target = (
                (group == "spawn warrior" and self._spawned_warriors < 2)
                or (group == "spawn farmer" and self._spawned_farmers < 2)
            )
            can_reserve_a_farmer = len(remaining) >= 3
            can_use_last_pair_for_target = (
                len(remaining) == len(farmers) and has_unmet_target
            )
            if not (can_reserve_a_farmer or can_use_last_pair_for_target):
                return False

            pair = [remaining.pop(), remaining.pop()]
            assignments.extend((c, group) for c in pair)
            wheat -= cost

            if group == "spawn warrior":
                self._spawned_warriors += 1
            else:
                self._spawned_farmers += 1
            return True

        # Prioritize the damage-dealing Warriors, then ensure Farmer spawns too.
        if self._spawned_warriors < 2:
            spawn_pair("spawn warrior", 12)
        if self._spawned_farmers < 2:
            spawn_pair("spawn farmer", 10)

        # Once both minimum targets are met, use genuinely surplus wheat for
        # more Warriors, while keeping at least one Farmer available to farm.
        if (
            self._spawned_warriors >= 2
            and wheat >= 24
            and len(remaining) >= 3
        ):
            spawn_pair("spawn warrior", 12)

        assignments.extend((c, "farm") for c in remaining)

        for component, group_name in assignments:
            environment.assign_group(component, group_name)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "attack")
            else:
                # Farmers belong in the Village rather than the Cave.
                environment.assign_group(component, "village")