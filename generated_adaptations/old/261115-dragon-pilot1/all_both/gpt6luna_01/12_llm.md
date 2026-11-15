The wheat check needs to account for every meal due this step before assigning a spawn pair. The updated strategy counts those meals, reserves enough wheat for them plus a small buffer, and only spends the remainder on spawning. Villagers are still explicitly assigned to a group every step, and Warrior returns remain staggered.

```py
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
        # Meals due this step are protected first. The extra buffer helps
        # avoid spending wheat needed for meals in the next few steps.
        safe_to_spend = max(0, wheat - meals_due - 2)
        spawn_group = None

        if (
            self._warrior_spawn_pairs < 2
            and len(available_farmers) >= 2
            and safe_to_spend >= 12
        ):
            spawn_group = "spawn warrior"
        elif (
            self._farmer_spawn_pairs < 2
            and len(available_farmers) >= 2
            and safe_to_spend >= 10
        ):
            spawn_group = "spawn farmer"

        if spawn_group is not None:
            for farmer in available_farmers[:2]:
                self._assign(environment, farmer, spawn_group)
            available_farmers = available_farmers[2:]

            if spawn_group == "spawn warrior":
                self._warrior_spawn_pairs += 1
            else:
                self._farmer_spawn_pairs += 1

        for farmer in available_farmers:
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for farmer in farmers:
            self._assign(environment, farmer, "village")

        returning = []
        attackers = []
        thresholds = (3, 3, 4)

        for warrior in warriors:
            age = self._age(warrior)
            threshold = thresholds[self._cohort(warrior)]
            if age >= 4 or age >= threshold:
                returning.append(warrior)
            else:
                attackers.append(warrior)

        # Do not let an age-3 return leave the Cave without an attacker.
        # Age-4 Warriors still return so they can eat before starving.
        if not attackers:
            safe_to_delay = [w for w in returning if self._age(w) < 4]
            if safe_to_delay:
                keeper = min(safe_to_delay, key=self._age)
                returning.remove(keeper)
                attackers.append(keeper)

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in returning:
            self._assign(environment, warrior, "village")
```