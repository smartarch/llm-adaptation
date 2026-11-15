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
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        assigned = set()

        # Eat before reaching the starvation-warning age. Reserve meals for
        # anyone already in the Village whose meal is due or imminent.
        meal_candidates = sorted(
            (c for c in components if self._age(c) >= 4),
            key=self._age,
            reverse=True,
        )
        for component in meal_candidates:
            if wheat > 0:
                self._assign(environment, component, "eat")
                wheat -= 1
                assigned.add(id(component))

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for warrior in warriors:
            if id(warrior) in assigned:
                continue
            # Avoid sending a villager away if their meal is due and food is
            # temporarily unavailable; farming may replenish the food supply.
            if self._age(warrior) >= 4:
                self._assign(environment, warrior, "farm")
            else:
                self._assign(environment, warrior, "cave")
            assigned.add(id(warrior))

        available_farmers = [f for f in farmers if id(f) not in assigned]

        # Keep a sizeable safety buffer for meals, including Warriors that
        # will arrive from the Cave on a later step.
        imminent_meals = sum(
            1 for c in components
            if id(c) not in assigned and self._age(c) >= 3
        )
        food_reserve = max(6, len(components) + 2) + imminent_meals

        spawn_group = None
        spawn_cost = 0
        if len(available_farmers) >= 2:
            if len(warriors) == 0 and self.warrior_spawn_events < 8:
                if wheat >= 12 + food_reserve:
                    spawn_group, spawn_cost = "spawn warrior", 12
            elif self.farmer_spawn_events < 2:
                if wheat >= 10 + food_reserve:
                    spawn_group, spawn_cost = "spawn farmer", 10
            elif self.warrior_spawn_events < 8:
                if wheat >= 12 + food_reserve:
                    spawn_group, spawn_cost = "spawn warrior", 12

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
                assigned.add(id(farmer))

            if spawn_group == "spawn farmer":
                self.farmer_spawn_events += 1
            else:
                self.warrior_spawn_events += 1

        # Always explicitly assign every remaining villager.
        for component in components:
            if id(component) not in assigned:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if getattr(environment.dragon, "hp", 0) <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]

        # Send one Warrior back at a time, starting at age 3 so they can
        # reach the Village and eat before the starvation warning.
        due = sorted(
            (w for w in warriors if self._age(w) >= 3),
            key=lambda w: (self._age(w), -getattr(w, "hp", 0)),
            reverse=True,
        )
        returning_id = id(due[0]) if due else None

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
            elif id(component) == returning_id:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")