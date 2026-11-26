from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    @staticmethod
    def _get(obj, name, default=0):
        return getattr(obj, name, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._get(environment.farm, "wheat", 0))
        dragon_hp = max(0, self._get(environment.dragon, "hp", 0))

        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        living_count = len(warriors) + len(farmers)
        warrior_count = len(warriors)

        remaining = list(villagers)
        assigned = set()

        def put(v, group):
            self._assign(environment, v, group)
            assigned.add(id(v))
            remaining.remove(v)

        # Eat first, so villagers can travel and fight without nearing starvation.
        hungry = sorted(
            (v for v in remaining
             if self._get(v, "steps_since_meal", 0) >= 4),
            key=lambda v: (
                self._get(v, "steps_since_meal", 0),
                -self._get(v, "hp", 0),
            ),
            reverse=True,
        )
        for v in hungry:
            if wheat <= 0:
                break
            put(v, "eat")
            wheat -= 1

        local_farmers = [
            v for v in remaining
            if self._get(v, "role", "") == "Farmer"
        ]

        spawn_group = None
        if dragon_hp > 0 and warrior_count == 0:
            # Ensure the first Warrior is produced as soon as possible.
            if len(remaining) >= 2 and wheat >= 12 + living_count:
                spawn_group = "spawn warrior"
        elif dragon_hp > 0 and living_count < 5 and len(local_farmers) >= 2:
            # Build a larger population and food economy before expanding the
            # fighting force.
            if wheat >= 10 + living_count:
                spawn_group = "spawn farmer"
        elif dragon_hp > 0 and warrior_count < 5:
            # With a base population established, keep replenishing Warriors.
            if len(remaining) >= 2 and wheat >= 12 + living_count:
                spawn_group = "spawn warrior"

        if spawn_group:
            # Prefer assigning Farmers to spawn groups, preserving Warriors
            # for the Cave whenever possible.
            candidates = sorted(
                remaining,
                key=lambda v: (
                    self._get(v, "role", "") != "Farmer",
                    self._get(v, "steps_since_meal", 0),
                ),
            )
            for v in candidates[:2]:
                put(v, spawn_group)

        # Keep food production going while sending available Warriors to fight.
        for v in list(remaining):
            role = self._get(v, "role", "")
            hp = self._get(v, "hp", 0)
            age = self._get(v, "steps_since_meal", 0)

            if dragon_hp > 0 and role == "Warrior" and hp > 0 and age < 4:
                put(v, "cave")
            elif dragon_hp > 0 and dragon_hp <= 15 and hp > 0 and age < 4:
                # When close to victory, even Farmers' damage can be decisive.
                put(v, "cave")
            else:
                put(v, "farm")

        for v in villagers:
            if id(v) not in assigned:
                self._assign(environment, v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, self._get(environment.dragon, "hp", 0))

        for v in components:
            age = self._get(v, "steps_since_meal", 0)
            hp = self._get(v, "hp", 0)
            role = self._get(v, "role", "")

            if dragon_hp <= 0:
                self._assign(environment, v, "village")
            elif age >= 4 or hp <= 3 or role == "Farmer":
                # Return before starvation, or before a wounded villager is
                # likely to be killed by another Dragon attack.
                self._assign(environment, v, "village")
            else:
                self._assign(environment, v, "attack")