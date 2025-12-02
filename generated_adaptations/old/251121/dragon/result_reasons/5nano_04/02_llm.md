Reasoning and strategy

Goal and constraints recap:
- All Warriors should move to the Cave to eventually attack the Dragon.
- All Farmers should stay in the Village (but can participate in spawning new villagers via dedicated spawn groups).
- Spawn groups:
  - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - "spawn warrior": for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- The Dragon starts with 50 HP and must be killed as fast as possible; it can attack back and can kill villagers.
- The Dragon must be attacked, and at least once in the first 15 steps.
- At least a few new villagers (Farmers and Warriors) should be spawned to increase the chance of killing the Dragon.
- All Warriors should attack after moving to the Cave; at least half should be in the Cave most of the time.

Strategy description:
- In assign_in_village (Villagers are in the Village):
  - Move all Warriors to the Cave (group "cave"), so they travel to the Dragon’s location.
  - Keep Farmers in the Village by default in the "farm" group to maximize wheat production.
  - Use spawn groups to create new villagers as wheat becomes available:
    - If there is at least 10 wheat and there are at least two Farmers, move two Farmers into the "spawn farmer" group to trigger Farmer spawning.
    - If there is at least 12 wheat and there are at least four Farmers, move two (additional) Farmers into the "spawn warrior" group to trigger Warrior spawning.
  - This approach ensures a quick attack setup (Warriors head to the cave early) and gradual growth of both Farmer and Warrior populations to improve DPS over time.
- In assign_in_cave (Villagers in the Cave):
  - All Warriors should be assigned to the "attack" group to guarantee they attack the Dragon.
  - Farmers should be kept in the Village (assigned to "village" group) so they can continue farming or be re-used for spawning in subsequent steps.
  - This arrangement guarantees that a) Warriors concentrate on Dragon DPS, b) Farmers stay to provide wheat/resources for spawning, and c) the Dragon is attacked early (due to Warriors arriving in the cave quickly).

Now the Python implementation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the cave to head to the fight.
        # - Keep Farmers in the village to farm (default to "farm" group).
        # - Use spawn groups to create new villagers based on wheat availability.
        # - Spawn farmers when wheat >= 10 (with 2 farmers in the spawn group).
        # - Spawn warriors when wheat >= 12 (with 2 additional farmers in the spawn warrior group).
        if not components:
            return

        # First, move all Warriors to the cave; put Farmers in farm by default.
        farmers = []
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")  # move to cave
            else:
                # Farmers stay in village and farm by default
                environment.assign_group(c, "farm")
                farmers.append(c)

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Try to spawn farmers if possible: need 2 villagers in 'spawn farmer' and 10 wheat
        if wheat >= 10 and len(farmers) >= 2:
            # Pick two farmers to assign to spawn farmer
            f1, f2 = farmers[0], farmers[1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            # Update wheat as a result of spawning (spawn mechanic is external; we only trigger the group)
            # Do not deduct wheat here; the environment updater handles it.

        # Try to spawn warriors if possible: need 2 villagers in 'spawn warrior' and 12 wheat
        # We'll use two more farmers if available
        if wheat >= 12 and len(farmers) >= 4:
            f3, f4 = farmers[2], farmers[3]
            environment.assign_group(f3, "spawn warrior")
            environment.assign_group(f4, "spawn warrior")

        # Note: We keep all Farmers roughly in Village (farm/spawn groups) and all Warriors in Cave (cave onward to attack).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave phase:
        # - All Warriors should attack (group "attack").
        # - Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")  # attack the Dragon
            else:
                environment.assign_group(c, "village")  # return to Village
```