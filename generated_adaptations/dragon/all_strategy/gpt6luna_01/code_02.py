from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_events = 0
        self.warrior_spawn_events = 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = getattr(environment.farm, "wheat", 0)
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors in the Village eat first if their meal is getting due;
        # otherwise, send them back to the Cave.
        for warrior in warriors:
            if self._age(warrior) >= 4:
                self._assign(environment, warrior, "eat")
                wheat = max(0, wheat - 1)
            else:
                self._assign(environment, warrior, "cave")

        # Farmers must eat before being used for spawning or farming.
        for farmer in farmers:
            if self._age(farmer) >= 4:
                self._assign(environment, farmer, "eat")
                wheat = max(0, wheat - 1)

        available_farmers = sorted(
            (f for f in farmers if self._age(f) < 4),
            key=self._age,
        )

        # Reserve food for farmers whose meals are due this step.
        meals_due = sum(1 for f in farmers if self._age(f) >= 4)
        meals_due += sum(1 for w in warriors if self._age(w) >= 4)

        spawn_group = None
        spawn_cost = 0

        # Prioritize producing Warriors so the Dragon can be attacked early.
        if (
            self.warrior_spawn_events < 2
            and len(available_farmers) >= 2
            and wheat >= 12 + meals_due
        ):
            spawn_group = "spawn warrior"
            spawn_cost = 12
            self.warrior_spawn_events += 1
        elif (
            self.farmer_spawn_events < 2
            and len(available_farmers) >= 2
            and wheat >= 10 + meals_due
        ):
            spawn_group = "spawn farmer"
            spawn_cost = 10
            self.farmer_spawn_events += 1

        spawned_workers = set()
        if spawn_group is not None:
            pair = available_farmers[:2]
            for farmer in pair:
                self._assign(environment, farmer, spawn_group)
                spawned_workers.add(id(farmer))
            wheat = max(0, wheat - spawn_cost)

        for farmer in farmers:
            if self._age(farmer) >= 4 or id(farmer) in spawned_workers:
                continue
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = getattr(environment.dragon, "hp", 0)
        if dragon_hp <= 0:
            for component in components:
                self._assign(environment, component, "village")
            return

        warriors = [c for c in components if c.role == "Warrior"]
        due_warriors = sorted(
            (w for w in warriors if self._age(w) >= 5),
            key=self._age,
            reverse=True,
        )
        active_warriors = [
            w for w in warriors
            if self._age(w) < 5 and getattr(w, "hp", 0) > 0
        ]

        # Return at most one due Warrior when others can continue attacking.
        returning_warrior = None
        if due_warriors and (len(active_warriors) > 0 or len(due_warriors) == 1):
            returning_warrior = due_warriors[0]

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village")
            elif component is returning_warrior:
                self._assign(environment, component, "village")
            elif getattr(component, "hp", 0) > 0 and self._age(component) < 6:
                self._assign(environment, component, "attack")
            else:
                self._assign(environment, component, "village")