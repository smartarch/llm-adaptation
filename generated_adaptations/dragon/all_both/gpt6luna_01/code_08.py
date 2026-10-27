from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cohorts = {}
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
        if key not in self._cohorts:
            self._cohorts[key] = self._next_cohort % 3
            self._next_cohort += 1
        return self._cohorts[key]

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
                self._assign(environment, warrior, "eat")
            else:
                self._assign(environment, warrior, "cave")

        wheat = getattr(environment.farm, "wheat", 0) or 0
        spawn_group = None

        # Favor Warriors to improve attack coverage; also spawn Farmers so
        # wheat production can support additional meals and spawns.
        if len(available_farmers) >= 2 and wheat >= 14:
            spawn_group = "spawn warrior"
            self._warrior_spawn_pairs += 1
        elif (
            len(available_farmers) >= 2
            and wheat >= 12
            and self._farmer_spawn_pairs < 2
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

        return_candidates = []
        attackers = []

        # Three cohorts provide staggered return times. A cohort can begin
        # returning at age 3; everyone must begin returning by age 4.
        thresholds = (3, 3, 4)
        for warrior in warriors:
            age = self._age(warrior)
            if age >= 4 or age >= thresholds[self._cohort(warrior)]:
                return_candidates.append(warrior)
            else:
                attackers.append(warrior)

        # Do not make an age-3 Warrior leave if that would leave nobody
        # attacking. They can attack this step and return at age 4.
        if not attackers:
            safe_to_delay = [
                w for w in return_candidates
                if self._age(w) < 4
            ]
            if safe_to_delay:
                keeper = min(safe_to_delay, key=self._age)
                return_candidates.remove(keeper)
                attackers.append(keeper)

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in return_candidates:
            self._assign(environment, warrior, "village")