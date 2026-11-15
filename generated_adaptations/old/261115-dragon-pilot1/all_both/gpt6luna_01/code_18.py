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
            # Build up Warrior numbers first, then add Farmers to improve
            # long-term wheat production. Continue spawning Warriors when
            # wheat allows, since they are needed to maintain Cave coverage.
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

        returning = []
        attackers = []

        if len(warriors) > 1:
            # Rotate the oldest Warrior home as soon as age 2. Keeping the
            # rest attacking staggers their meal trips and avoids synchronized
            # returns that would empty the Cave.
            oldest = max(warriors, key=self._age)
            if self._age(oldest) >= 2:
                returning.append(oldest)

            for warrior in warriors:
                if warrior is not oldest:
                    attackers.append(warrior)

            # At age 4, Warriors must return to reach the Village and eat
            # before the starvation deadline.
            for warrior in warriors:
                if self._age(warrior) >= 4 and warrior not in returning:
                    returning.append(warrior)
                    if warrior in attackers:
                        attackers.remove(warrior)
        elif warriors:
            warrior = warriors[0]
            if self._age(warrior) >= 4:
                returning.append(warrior)
            else:
                attackers.append(warrior)

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in returning:
            self._assign(environment, warrior, "village")