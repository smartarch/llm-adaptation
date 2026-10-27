from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_events = 0
        self.warrior_spawn_events = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0)

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = getattr(environment.farm, "wheat", 0)
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Eat before the warning threshold so travel and action timing cannot
        # push a villager into starvation.
        for component in components:
            if self._age(component) >= 4:
                self._assign(environment, component, "eat")
                wheat = max(0, wheat - 1)

        for warrior in warriors:
            if self._age(warrior) < 4:
                self._assign(environment, warrior, "cave")

        available_farmers = [f for f in farmers if self._age(f) < 4]
        meals_due = sum(1 for c in components if self._age(c) >= 4)

        spawn_group = None
        spawn_cost = 0

        # Build the attacking force first. Once established, add Farmers when
        # the stored food can cover both spawning and near-term meals.
        if (
            self.warrior_spawn_events < 4
            and len(available_farmers) >= 2
            and wheat >= 12 + meals_due
        ):
            spawn_group, spawn_cost = "spawn warrior", 12
        elif (
            self.farmer_spawn_events < 2
            and len(available_farmers) >= 2
            and wheat >= 25 + meals_due
        ):
            spawn_group, spawn_cost = "spawn farmer", 10
        elif (
            self.warrior_spawn_events < 8
            and len(available_farmers) >= 2
            and wheat >= 12 + meals_due
        ):
            spawn_group, spawn_cost = "spawn warrior", 12

        spawned = set()
        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                spawned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1
            wheat = max(0, wheat - spawn_cost)

        for farmer in farmers:
            if self._age(farmer) >= 4 or id(farmer) in spawned:
                continue
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]

        # Return Warriors early enough to travel to the Village and eat.
        # Stagger age-3 returns when possible; anyone at age 4 must return.
        age_three = sorted(
            (w for w in warriors if self._age(w) == 3),
            key=lambda w: getattr(w, "hp", 0),
        )
        age_four_or_more = [w for w in warriors if self._age(w) >= 4]
        returning = set(age_four_or_more)

        active_others = [
            w for w in warriors
            if w not in returning
            and getattr(w, "hp", 0) > 0
        ]
        if age_three and active_others:
            returning.add(age_three[0])

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
            elif component in returning or getattr(component, "hp", 0) <= 0:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")