The attack gaps persisted because the earlier cohort thresholds could send the first two Warriors home at the same age, and spawning stopped after a small fixed number of pairs. This version staggers the first Warrior’s return earlier than the others, continues prioritizing Warrior spawns when wheat allows, and reserves wheat for meals due now. Farmers still spawn too once Warrior recruitment has had priority.

```py
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
            self._cohort_by_id[key] = self._next_cohort % 4
            self._next_cohort += 1
        return self._cohort_by_id[key]

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
        spendable_wheat = max(0, wheat - meals_due - 2)
        spawn_group = None

        # Keep adding Warriors while wheat permits; alternate in Farmers
        # after Warrior recruitment has started.
        if len(available_farmers) >= 2 and spendable_wheat >= 12:
            if self._warrior_spawn_pairs < 2 or self._warrior_spawn_pairs <= self._farmer_spawn_pairs:
                spawn_group = "spawn warrior"
                self._warrior_spawn_pairs += 1
            elif spendable_wheat >= 10:
                spawn_group = "spawn farmer"
                self._farmer_spawn_pairs += 1
        elif len(available_farmers) >= 2 and spendable_wheat >= 10:
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
        attackers = []

        # One cohort returns at age 3; the others return at age 4.
        # This spreads trips to the Village across steps.
        for warrior in warriors:
            age = self._age(warrior)
            threshold = 3 if self._cohort(warrior) == 0 else 4
            if age >= threshold:
                returning.append(warrior)
            else:
                attackers.append(warrior)

        # Keep a Warrior attacking if another Warrior is already returning.
        # Do not delay anyone at age 4: they need to get back and eat.
        if not attackers and len(returning) > 1:
            safe_to_keep = [w for w in returning if self._age(w) < 4]
            if safe_to_keep:
                keeper = min(safe_to_keep, key=self._age)
                returning.remove(keeper)
                attackers.append(keeper)

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in returning:
            self._assign(environment, warrior, "village")
```