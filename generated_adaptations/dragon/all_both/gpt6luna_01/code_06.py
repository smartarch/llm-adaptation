from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cohort_by_id = {}
        self._next_cohort = 0
        self._warrior_spawn_pairs = 0
        self._farmer_spawn_pairs = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0) or 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def _cohort(self, warrior):
        key = id(warrior)
        if key not in self._cohort_by_id:
            self._cohort_by_id[key] = self._next_cohort % 3
            self._next_cohort += 1
        return self._cohort_by_id[key]

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        available_farmers = []
        for farmer in farmers:
            if self._age(farmer) >= 5:
                self._assign(environment, farmer, "eat")
            else:
                available_farmers.append(farmer)

        for warrior in warriors:
            if self._age(warrior) >= 3:
                # Eat first; do not send a hungry Warrior back to the Cave.
                self._assign(environment, warrior, "eat")
            else:
                self._assign(environment, warrior, "cave")

        wheat = getattr(environment.farm, "wheat", 0) or 0
        # Leave some wheat available for meals.
        reserve = 2
        spawn_group = None

        if (
            self._warrior_spawn_pairs < 2
            and len(available_farmers) >= 2
            and wheat >= 12 + reserve
        ):
            spawn_group = "spawn warrior"
            self._warrior_spawn_pairs += 1
        elif (
            self._farmer_spawn_pairs < 2
            and len(available_farmers) >= 2
            and wheat >= 10 + reserve
        ):
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

        returning = []
        attacking = []

        # Stagger meal rotations. A Warrior returning at age 2 or 3 reaches
        # the Village in time to eat before becoming too hungry; age 4 is the
        # latest safe return threshold.
        thresholds = (2, 3, 4)
        for warrior in warriors:
            threshold = thresholds[self._cohort(warrior)]
            if self._age(warrior) >= threshold:
                returning.append(warrior)
            else:
                attacking.append(warrior)

        # If this cohort is the only one in the Cave, continue attacking
        # while it is still safe to do so; never delay a return past age 4.
        if not attacking:
            safe_to_keep = [
                w for w in returning
                if self._age(w) < 4
            ]
            if safe_to_keep:
                keeper = min(safe_to_keep, key=self._age)
                attacking.append(keeper)
                returning.remove(keeper)

        for warrior in attacking:
            self._assign(environment, warrior, "attack")

        for warrior in returning:
            self._assign(environment, warrior, "village")