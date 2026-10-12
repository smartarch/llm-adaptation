Strategy and reasoning

Goal-driven adaptation:
- Core rules: All Warriors must move to the Cave to attack the Dragon. All Farmers stay in the Village (to farm and to enable spawning). The game supports spawning new villagers via two special groups: "spawn farmer" (needs 2 villagers in that group and 10 wheat) and "spawn warrior" (needs 2 villagers in that group and 12 wheat). The Dragons’ counterattack can kill villagers, so we should keep a healthy number of villagers alive and spawn more to increase DPS and overall farmed wheat.
- Attack plan: Put all Warriors into the Cave and assign them to the "attack" group once in the Cave so they attack the Dragon. This ensures the half of the Warrior population is in the Cave most of the time, satisfying the requirement to have many Warriors in the Cave and attacking the Dragon.
- Wheat-aware spawning: Farmers in Village will be divided into three subgroups to trigger spawning:
  - "spawn farmer": for every two farmers in this group and 10 wheat, a new Farmer is spawned.
  - "spawn warrior": for every two farmers in this group and 12 wheat, a new Warrior is spawned.
  - The remaining farmers go to "farm" (continue farming).
  The strategy uses the Farm’s wheat (environment.farm.wheat) to determine how many spawns can be triggered, prioritizing spawning farmers (to increase long-term wheat production and population) and then, if wheat remains, spawning warriors (to boost DPS).
- Early aggression: Warriors are already in the Cave from the Village stage, so the Dragon will be attacked early (well before step 15). If there are no Warriors initially, the spawn logic may still create Warriors in subsequent steps; however, with the given constraint that Warriors should be moved to the Cave, the primary path is to ensure Warriors are always routed to the Cave and attacked.
- Movement to satisfy constraints: In cave assignments, Farmers are moved back to the Village (to ensure all Farmers stay in Village). This enforces the rule that Farmers stay in the Village and only Warriors go to the Cave/attack.

Behavior in steps:
- assign_in_village:
  - Move all Warriors to the Cave (group "cave").
  - For Farmers, compute how many spawns we can trigger with current wheat and number of farmers.
  - Allocate 2*kf farmers to "spawn farmer" (each such pair with 10 wheat spawns a new Farmer).
  - With any remaining wheat, allocate 2*kw farmers to "spawn warrior" (each such pair with 12 wheat spawns a new Warrior).
  - Remaining Farmers go to "farm".
- assign_in_cave:
  - Warriors go to "attack" (to fight the Dragon).
  - Farmers in the Cave return to the Village (group "village").

This simple heuristic ensures:
- The Dragon is attacked early (by Warriors in the Cave).
- All Warriors end up in the Cave to attack.
- Farmers stay in the Village and contribute to spawning and farming.
- We spawn both Farmers and Warriors as Wheat allows, providing a path to increasing both DPS and Wheat production.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village to farm wheat
        - cave: go to the Cave (for Warriors)
        - spawn farmer: for every 2 villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every 2 villagers in this group and 12 wheat, spawn a Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should move to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village, but we may use some to spawn
        # Current wheat available for spawning
        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine how many spawns we can trigger
        # Each spawn farmer uses 2 farmers and 10 wheat -> one new Farmer
        max_farm_spawns = len(farmers) // 2
        kf = min(max_farm_spawns, available_wheat // 10)

        # Wheat remaining after spawning farmers
        remaining_wheat = available_wheat - (kf * 10)

        # Each spawn warrior uses 2 farmers and 12 wheat -> one new Warrior
        max_war_spawns = (len(farmers) - 2 * kf) // 2
        kw = min(max_war_spawns, remaining_wheat // 12)

        # Allocate farmers to groups
        idx = 0

        # Assign 2*kf farmers to "spawn farmer"
        for _ in range(2 * kf):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign 2*kw farmers to "spawn warrior"
        for _ in range(2 * kw):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to "farm" (stay in Village and farm)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Note: If there are no farmers, nothing else to do here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors should attack the Dragon
        - cave: stay in the Cave (if any non-Warrior ends up here, keep them here)
        - village: go back to Village (Farmers should return to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in Village
                environment.assign_group(c, "village")
```