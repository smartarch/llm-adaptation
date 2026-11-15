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
            if spendable >= 12 and self._warrior_spawn_pairs < 4:
                spawn_group = "spawn warrior"
                self._warrior_spawn_pairs += 1
            elif spendable >= 10 and self._farmer_spawn_pairs < 2:
                spawn_group = "spawn farmer"
                self._farmer_spawn_pairs += 1

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

        # Keep Warriors fighting through age 3. At age 4 they must begin the
        # trip home so they can eat in the Village before reaching age 5.
        due_to_return = [w for w in warriors if self._age(w) >= 4]
        attackers = [w for w in warriors if self._age(w) < 4]

        # When several Warriors become due together, return only one at a
        # time if doing so still leaves an attacker in the Cave. This spreads
        # their return trips instead of evacuating the Cave simultaneously.
        if not attackers and len(due_to_return) > 1:
            # Age-4 Warriors cannot safely be delayed: they must return now.
            # Keep one attacking only when there are no other attackers and
            # that Warrior is still below the age-5 meal deadline.
            keeper = min(due_to_return, key=self._age)
            if self._age(keeper) < 5:
                attackers.append(keeper)
                due_to_return.remove(keeper)

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in due_to_return:
            self._assign(environment, warrior, "village")