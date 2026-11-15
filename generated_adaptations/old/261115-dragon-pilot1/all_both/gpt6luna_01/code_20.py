from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_pairs = 0
        self._farmer_spawn_pairs = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0) or 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        available_farmers = []
        meals_due = 0

        for farmer in farmers:
            if self._age(farmer) >= 5:
                self._assign(environment, farmer, "eat")
                meals_due += 1
            else:
                available_farmers.append(farmer)

        for warrior in warriors:
            if self._age(warrior) >= 3:
                self._assign(environment, warrior, "eat")
                meals_due += 1
            else:
                self._assign(environment, warrior, "cave")

        wheat = getattr(environment.farm, "wheat", 0) or 0
        spendable = max(0, wheat - meals_due - 2)
        spawn_group = None

        if len(available_farmers) >= 2:
            if self._warrior_spawn_pairs < 3 and spendable >= 12:
                spawn_group = "spawn warrior"
                self._warrior_spawn_pairs += 1
            elif self._farmer_spawn_pairs < 2 and spendable >= 10:
                spawn_group = "spawn farmer"
                self._farmer_spawn_pairs += 1
            elif spendable >= 12:
                spawn_group = "spawn warrior"
                self._warrior_spawn_pairs += 1

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
            available_farmers = available_farmers[2:]

        for farmer in available_farmers:
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for farmer in farmers:
            self._assign(environment, farmer, "village")

        returning_ids = set()

        if len(warriors) > 1:
            # Rotate the oldest Warrior home once they have spent two steps
            # without a meal; other Warriors remain available to attack.
            oldest = max(warriors, key=self._age)
            if self._age(oldest) >= 2:
                returning_ids.add(id(oldest))

        # Warriors aged 4 must head back now so they can eat in the Village
        # before reaching the starvation deadline.
        for warrior in warriors:
            if self._age(warrior) >= 4:
                returning_ids.add(id(warrior))

        # Assign each Warrior exactly once, using identity rather than
        # component equality when deciding whether they are returning.
        for warrior in warriors:
            group = "village" if id(warrior) in returning_ids else "attack"
            self._assign(environment, warrior, group)