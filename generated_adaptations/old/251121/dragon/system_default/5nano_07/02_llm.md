Reasoning and adaptation strategy

Goal and constraints recap:
- All Warriors should go to the Cave and then attack the Dragon.
- All Farmers should stay in the Village and farm (and potentially contribute to spawning new villagers).
- There are optional spawn groups: "spawn farmer" and "spawn warrior" that create new villagers given some wheat. Spawning can help grow your force, but it also relies on wheat supplies and uses villagers' time instead of farming/attacking.

Strategy outline:
- Primary plan: keep all Warriors in the cave to maximize DPS early, and keep Farmers in the village to farm wheat.
- Spawn logic (optional enhancement): leverage farming wheat to spawn new Farmers when feasible. Specifically, compute how many new Farmers can be spawned this step using the current number of Farmers and the wheat available on the Farm. We assign the smallest subset of Farmers to the "spawn farmer" group (in pairs) to produce as many new Farmers as allowed by wheat. The remaining Farmers stay in the "farm" group to continue producing wheat.
  - Spawn calculation: s = min(number_of_farmers_in_village // 2, farm.wheat // 10). Then assign 2*s Farmers to "spawn farmer" and the rest to "farm".
  - This approach ensures we do not spawn more than the resource and manpower allow and keeps Farmers contributing via farming when not spawning.
- Cave assignment: Warriors go to "attack"; Farmers go to "village" (they stay in the village and are out of the cave while not farming).

Implementation notes:
- The class SmartAdaptation derives from the provided base DragonHuntAdaptation.
- In assign_in_village, we:
  - Send all Warriors to the cave.
  - Partition Farmers between "spawn farmer" (to enable spawning) and "farm" (to continue producing wheat), based on available wheat.
- In assign_in_cave, we:
  - Send all Warriors to the "attack" group.
  - Send all Farmers to the "village" group.

This approach satisfies the requirement that every component is assigned to exactly one group, and it explicitly reassigns components to the required groups. It also leaves room for straightforward future tweaks (e.g., enabling a “spawn warrior” path if wheat is abundant).

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "cave": for Warriors to go to the Cave
        - "farm" or "spawn farmer": for Farmers to farm or spawn new farmers
        Spawn strategy:
        - Use available wheat on the Farm to determine how many new Farmers can be spawned:
          s = min(number_of_farmers_in_village // 2, farm.wheat // 10)
        - Assign 2*s Farmers to "spawn farmer" (to spawn s new Farmers)
        - Assign the remaining Farmers to "farm"
        Warriors are assigned to "cave" (they will go to the Cave)
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn farmer logic
        available_wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)
        # Number of new farmers that can be spawned this step
        s = min(n_farmers // 2, available_wheat // 10)

        # 3) Assign farmers to either spawn farmer or farm
        # First 2*s farmers go to "spawn farmer" group, rest go to "farm"
        for idx, c in enumerate(farmers):
            if idx < 2 * s:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave:
        - Warriors -> "attack" (Attack the Dragon)
        - Farmers  -> "village" (Go back to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```