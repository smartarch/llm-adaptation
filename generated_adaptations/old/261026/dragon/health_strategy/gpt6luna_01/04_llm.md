The earlier strategy stopped spawning Warriors after two spawn attempts, leaving the Cave force vulnerable to attrition. This version continues recruiting Warriors whenever there are two Farmers available and enough wheat, after first attempting to spawn two Farmers. Warriors with only 1 HP retreat rather than risk being lost to Dragon retaliation; they join the attack if the Dragon is close enough to finish. Farmers in the Cave return to the Village, and every component is explicitly assigned on each callback.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_attempts = 0

    @staticmethod
    def _groups(group_ids):
        return {name: name for name in group_ids}

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = self._groups(group_ids)
        farmers = []
        dragon_hp = environment.dragon.hp

        for component in components:
            if component.role == "Warrior":
                # Keep critically wounded Warriors out of the Cave unless
                # their damage could finish the Dragon immediately.
                if component.hp <= 1 and dragon_hp > 3:
                    environment.assign_group(component, groups["farm"])
                else:
                    environment.assign_group(component, groups["cave"])
            else:
                farmers.append(component)

        wheat = environment.farm.wheat
        spawn_group = None

        # Meet the requested Farmer-spawning target first.
        if self.farmer_spawn_attempts < 2 and wheat >= 10:
            spawn_group = "spawn farmer"
        # Then keep replacing Warriors lost to Dragon retaliation.
        elif wheat >= 12:
            spawn_group = "spawn warrior"

        if spawn_group is not None and len(farmers) >= 2:
            for component in farmers[:2]:
                environment.assign_group(component, groups[spawn_group])
            farmers = farmers[2:]

            if spawn_group == "spawn farmer":
                self.farmer_spawn_attempts += 1

        for component in farmers:
            environment.assign_group(component, groups["farm"])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = self._groups(group_ids)
        dragon_hp = environment.dragon.hp

        cave_warrior_damage = sum(
            3 for component in components if component.role == "Warrior"
        )
        can_finish_now = dragon_hp <= cave_warrior_damage

        for component in components:
            if component.role == "Farmer":
                environment.assign_group(component, groups["village"])
            elif component.hp <= 1 and not can_finish_now:
                environment.assign_group(component, groups["village"])
            else:
                environment.assign_group(component, groups["attack"])
```