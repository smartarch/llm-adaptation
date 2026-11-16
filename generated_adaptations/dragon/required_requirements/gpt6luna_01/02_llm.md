The strategy feeds villagers before they approach starvation, sends healthy warriors to attack as soon as they are ready, and returns cave warriors to the Village in time to eat. It uses fresh villagers—preferentially farmers—to spawn two warriors and one farmer when wheat is available, while assigning every villager on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    @staticmethod
    def _group_id(group_ids, name):
        # The valid group names are also the group IDs.
        return name if name in group_ids else group_ids[name]

    @staticmethod
    def _assign(environment, component, group_id):
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = max(0, environment.farm.wheat)

        # Feed villagers with the greatest need first. Warriors are fed at
        # three steps since their last meal so they can travel to the Cave fresh.
        needing_food = [
            c for c in components
            if c.steps_since_meal >= 4
            or (c.role == "Warrior" and c.steps_since_meal >= 3)
        ]
        needing_food.sort(
            key=lambda c: (c.steps_since_meal, -c.hp), reverse=True
        )

        assigned = {}
        for c in needing_food:
            if wheat >= 1:
                self._assign(environment, c, self._group_id(group_ids, "eat"))
                assigned[id(c)] = "eat"
                wheat -= 1

        # Use fresh farmers for spawning first. Fresh warriors are a fallback,
        # so warriors can otherwise leave for the Cave promptly.
        available = [
            c for c in components
            if id(c) not in assigned and c.steps_since_meal <= 2
        ]
        available.sort(key=lambda c: (c.role != "Farmer", c.steps_since_meal))

        def take_pair():
            if len(available) < 2:
                return None
            pair = available[:2]
            del available[:2]
            return pair

        # Produce the required warriors as early as wheat and eligible villagers allow.
        while self.spawned_warriors < 2 and wheat >= 12:
            pair = take_pair()
            if pair is None:
                break
            for c in pair:
                self._assign(environment, c, self._group_id(group_ids, "spawn warrior"))
                assigned[id(c)] = "spawn warrior"
            wheat -= 12
            self.spawned_warriors += 1

        # Spawn at least one farmer as well.
        if self.spawned_farmers < 1 and wheat >= 10:
            pair = take_pair()
            if pair is not None:
                for c in pair:
                    self._assign(environment, c, self._group_id(group_ids, "spawn farmer"))
                    assigned[id(c)] = "spawn farmer"
                wheat -= 10
                self.spawned_farmers += 1

        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                # Do not send a warrior who should eat first.
                if c.steps_since_meal < 3:
                    self._assign(environment, c, self._group_id(group_ids, "cave"))
                else:
                    # If wheat was unavailable for a meal, keep the warrior
                    # in the Village rather than sending them out hungry.
                    self._assign(environment, c, self._group_id(group_ids, "farm"))
            else:
                self._assign(environment, c, self._group_id(group_ids, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior":
                self._assign(environment, c, self._group_id(group_ids, "village"))
            elif c.steps_since_meal >= 4:
                # Moving back now leaves time to eat in the Village before starvation.
                self._assign(environment, c, self._group_id(group_ids, "village"))
            else:
                self._assign(environment, c, self._group_id(group_ids, "attack"))
```