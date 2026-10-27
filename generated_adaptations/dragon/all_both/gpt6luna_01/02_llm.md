The strategy sends fed Warriors to the Cave immediately and keeps them attacking, while returning them to the Village before they risk missing a meal. Farmers stay in the Village, eat when due, and otherwise farm or spawn new villagers. Spawning is limited to two attempts for each role and is delayed when wheat is needed for meals. Cave assignments prioritize keeping at least one Warrior attacking when several Warriors are due to return.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # A pair assigned to a spawn group produces one villager.
        self._farmer_spawn_attempts = 0
        self._warrior_spawn_attempts = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0) or 0

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Feed anyone who needs to eat before being sent away or put to work.
        available_farmers = []
        for villager in farmers:
            if self._age(villager) >= 5:
                self._assign(environment, villager, "eat")
            else:
                available_farmers.append(villager)

        for warrior in warriors:
            # A Warrior at age 3 or more eats before travelling to the Cave.
            if self._age(warrior) >= 3:
                self._assign(environment, warrior, "eat")
            else:
                self._assign(environment, warrior, "cave")

        # Spawn using pairs of Farmers, while preserving a small food reserve.
        wheat = getattr(environment.farm, "wheat", 0) or 0
        reserve = 2
        can_spawn_farmer = (
            self._farmer_spawn_attempts < 2
            and wheat >= 10 + reserve
            and len(available_farmers) >= 2
        )
        can_spawn_warrior = (
            self._warrior_spawn_attempts < 2
            and wheat >= 12 + reserve
            and len(available_farmers) >= 2
        )

        # Alternate the spawn types when both are affordable so neither is
        # indefinitely postponed.
        if can_spawn_farmer and can_spawn_warrior:
            spawn_order = (
                ("spawn farmer", "farmer")
                if self._farmer_spawn_attempts <= self._warrior_spawn_attempts
                else ("spawn warrior", "warrior")
            )
        elif can_spawn_farmer:
            spawn_order = ("spawn farmer", "farmer")
        elif can_spawn_warrior:
            spawn_order = ("spawn warrior", "warrior")
        else:
            spawn_order = None

        if spawn_order is not None:
            group_name, role_name = spawn_order
            pair = available_farmers[:2]
            for villager in pair:
                self._assign(environment, villager, group_name)
            del available_farmers[:2]

            if role_name == "farmer":
                self._farmer_spawn_attempts += 1
            else:
                self._warrior_spawn_attempts += 1

        # All remaining Farmers stay in the Village and work.
        for farmer in available_farmers:
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers belong in the Village. Warriors return in time to eat:
        # travelling home at age 4 allows them to eat on the following step.
        due_to_return = [w for w in warriors if self._age(w) >= 4]
        attackers = [w for w in warriors if self._age(w) < 4]

        # If every Warrior is due to return, keep the least-overdue one
        # attacking for this step when there is another Warrior to rotate in.
        if not attackers and len(due_to_return) > 1:
            keeper = min(due_to_return, key=self._age)
            attackers = [keeper]
            due_to_return = [w for w in due_to_return if w is not keeper]

        for farmer in farmers:
            self._assign(environment, farmer, "village")

        for warrior in attackers:
            self._assign(environment, warrior, "attack")

        for warrior in due_to_return:
            self._assign(environment, warrior, "village")
```