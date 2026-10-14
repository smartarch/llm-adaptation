## Strategy: Warriors fight, Farmers farm and breed

The strategy splits the roles by their strengths:

- **Warriors** (6 HP, 3 damage) are sent to the Cave and attack the Dragon every step. Warriors with 1 HP or less are pulled back to the Village so they can survive and be reused later. They are the main source of damage, and sending them early covers the requirement to attack in the first 15 steps.
- **Farmers** (4 HP, 5 wheat) stay in the Village. They farm by default, and farmers in the Cave are sent back. Farmers are the wheat engine that pays for spawning.
- **Spawning** uses a counter-based cap. A pair of farmers is put in "spawn warrior" when wheat is at least 12, and a pair goes to "spawn farmer" when wheat is at least 10. Each type is capped at two spawns, so the strategy reaches the goal of at least two of each role without wasting wheat. Spawn requests are only issued when there are at least two farmers in the Village, because the spawn needs two villagers in the group.

The spawn counters are a heuristic because the strategy cannot directly observe whether a spawn succeeded. Capping each type at two spawns keeps the logic simple and bounded.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Heuristic counters for requested spawns (each type capped at 2)
        self.spawn_requests_farmer = 0
        self.spawn_requests_warrior = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to fight the dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide which spawn (if any) to perform this step.
        # Spawning needs two villagers in the spawn group, so we need >= 2 farmers.
        spawn_group_members = []
        spawn_target = None
        if len(farmers) >= 2:
            if self.spawn_requests_warrior < 2 and wheat >= 12:
                spawn_target = "spawn warrior"
                self.spawn_requests_warrior += 1
            elif self.spawn_requests_farmer < 2 and wheat >= 10:
                spawn_target = "spawn farmer"
                self.spawn_requests_farmer += 1

        if spawn_target is not None:
            spawn_group_members = farmers[:2]

        # Assign the spawn pair (if any), the rest of the farmers keep farming
        for f in farmers:
            if f in spawn_group_members:
                environment.assign_group(f, spawn_target)
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Keep attacking while healthy; retreat nearly dead warriors
                if c.hp > 1:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")
            else:
                # Farmers do not fight; they return to the village to farm
                environment.assign_group(c, "village")
```