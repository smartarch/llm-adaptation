The strategy sends every warrior from the Village to the Cave and has every warrior there attack. Farmers remain in the Village, where they farm unless a pair is assigned to spawn a villager. It prioritizes spawning two farmers, then two warriors; when resources and farmers allow, it continues spawning warriors while the Dragon is alive. Every component is explicitly assigned on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._planned_farmers = 0
        self._planned_warriors = 0
        self._last_spawn_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        farmers = [v for v in villagers if v.role == "Farmer"]

        spawn_group = None
        spawn_cost = 0

        # Spawn a couple of farmers first, helping build the workforce.
        if (
            len(farmers) >= 2
            and self._planned_farmers < 2
            and self._last_spawn_step != step
        ):
            spawn_cost = 10
            # Allow a bootstrap spawn even when both current farmers are needed.
            reserve = 0 if len(farmers) == 2 else 5
            if environment.farm.wheat >= spawn_cost + reserve:
                spawn_group = "spawn farmer"

        # Then build the warrior force, and continue reinforcing it if possible.
        if spawn_group is None and len(farmers) >= 3 and self._last_spawn_step != step:
            dragon_alive = environment.dragon.hp > 0
            wants_warrior = self._planned_warriors < 2 or dragon_alive
            if wants_warrior and dragon_alive and environment.farm.wheat >= 17:
                spawn_group = "spawn warrior"
                spawn_cost = 12

        # Warriors in the Village always move to the Cave.
        for villager in villagers:
            if villager.role == "Warrior":
                environment.assign_group(villager, "cave")

        # Assign at most two farmers to a spawn group; explicitly assign all
        # remaining farmers to the farm.
        selected = set(farmers[:2]) if spawn_group is not None else set()
        for farmer in farmers:
            if farmer in selected:
                environment.assign_group(farmer, spawn_group)
            else:
                environment.assign_group(farmer, "farm")

        if spawn_group == "spawn farmer":
            self._planned_farmers += 1
            self._last_spawn_step = step
        elif spawn_group == "spawn warrior":
            self._planned_warriors += 1
            self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if villager.role == "Warrior":
                environment.assign_group(villager, "attack")
            else:
                # Farmers do not fight; send them back to the Village.
                environment.assign_group(villager, "village")
```