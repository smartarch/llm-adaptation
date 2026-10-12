Reasoning and adaptation strategy

Goal alignment:
- Kill the Dragon as fast as possible.
- Ensure the Dragon is attacked at least once within the first 15 steps.
- All Warriors should end up in the Cave to attack the Dragon.
- All Farmers should stay in the Village (though they can contribute by farming for wheat or spawning new villagers).
- Spawn both new Farmers and new Warriors to boost numbers and DPS.
- Keep a majority (at least half) of Warriors in the Cave to ensure ongoing DPS.

Strategy overview:
- Village stage:
  - Move all existing Warriors to the Cave (so they can attack the Dragon).
  - Keep Farmers in the Village and use them to generate wheat by farming.
  - Use a simple spawning plan to create new villagers when resources allow:
    - If there are at least 2 Farmers and the Farm has at least 10 wheat, designate 2 Farmers to the “spawn farmer” group to create new Farmers.
    - If there are at least 2 Farmers left after that and the Farm has at least 12 wheat, designate another 2 Farmers to the “spawn warrior” group to create new Warriors.
    - The remaining Farmers stay in the “farm” group to continue producing wheat.
  - This plan ensures some immediate farming (to unlock spawns) and some spawns to boost numbers, while ensuring Warriors move to cave promptly.
- Cave stage:
  - Move all Warriors to the “attack” group (they attack the Dragon).
  - Move all Farmers back to the Village (they should stay in village as per requirement).
  - This keeps the majority of Warriors in the cave while ensuring Farmers spend most time in the Village.

Rationale for spawn design:
- Spawning requires two villagers in a spawn group and a Wheat threshold (10 for Farmers, 12 for Warriors). By initially designating two Farmers to each spawn group when wheat is available, we create new Farmers or Warriors in the next steps, increasing DPS and number of attackers. Farmers stay in Village or spawn groups, Warriors move to cave to attack.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be used immediately by Warriors)
        - spawn farmer: for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Keep Farmers in Village and decide on spawning
        if farmers:
            # Default: all farmers stay in farm (to produce wheat)
            for f in farmers:
                environment.assign_group(f, "farm")

            # Try to designate two Farmers to spawn another Farmer (spawn farmer)
            # and, if possible, two to spawn Warriors (spawn warrior)
            # Only attempt if we have at least 2 farmers for the group
            if len(farmers) >= 2:
                wheat = getattr(environment.farm, "wheat", 0)

                # Spawn 1 new Farmer if there's enough wheat (10) and 2 villagers in group
                if wheat >= 10:
                    to_spawn_farmer = farmers[:2]
                    for c in to_spawn_farmer:
                        environment.assign_group(c, "spawn farmer")

                    # After assigning some to spawn farmer, see if we can spawn warriors too
                    remaining_for_warrior = farmers[2:]
                    if len(remaining_for_warrior) >= 2:
                        wheat_after = getattr(environment.farm, "wheat", 0)
                        if wheat_after >= 12:
                            to_spawn_warrior = remaining_for_warrior[:2]
                            for c in to_spawn_warrior:
                                environment.assign_group(c, "spawn warrior")

        # If there are no farmers, nothing to spawn; Warriors (if any) already moved to cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers should return to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                environment.assign_group(c, "village")
```