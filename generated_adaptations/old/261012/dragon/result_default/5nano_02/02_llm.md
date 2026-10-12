Strategy and reasoning:
- Objective: Kill the Dragon as fast as possible by structuring villagers’ movements and spawning in a way that maximizes damage output while ensuring survival and resource availability.
- Core rules we must respect:
  - All Warriors should go to the Cave to attack the Dragon.
  - All Farmers should stay in the Village to farm (to produce wheat) or participate in spawning new villagers (both Farmers and Warriors can be spawned; spawning consumes wheat and requires at least two villagers in the spawn group).
  - Spawning mechanics: 
    - To spawn a Farmer, at least two villagers must be in the "spawn farmer" group and at least 10 wheat must be available.
    - To spawn a Warrior, at least two villagers must be in the "spawn warrior" group and at least 12 wheat must be available.
- Practical adaptation approach:
  - In assign_in_village:
    - Keep Warriors in the Cave by assigning all Warriors to the "cave" group.
    - For Farmers, use a simple spawning heuristic: if there are at least two Farmers and at least 10 wheat, allocate two Farmers to the "spawn farmer" group to enable Farmer spawning; assign the remaining Farmers to the "farm" group.
    - Do not use the "spawn warrior" group here to preserve the directive that all Warriors should go to the Cave (attack).
  - In assign_in_cave:
    - Ensure Warriors go to "attack" to actively damage the Dragon.
    - Farmers in the Cave should head back to the Village to continue farming or spawning, so assign Farmers to the "village" group.
- This strategy emphasizes a steady wheat supply via Farmers in Village, with a small, deterministic spawn action to gradually grow the population if resources permit, while ensuring high DPS through Warriors attacking the Dragon.

Code (Python):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: stay in Village and farm
        - cave: go to the Cave (not used here for Warriors, but defined)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a new Farmer
        - spawn warrior: not used in this strategy to honor "All Warriors should go to the Cave" rule
        """
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Decide which farmers go to spawning and which go to farming
        spawn_farmers = []
        remaining_farmers = []

        # If we have at least two farmers and enough wheat, enable a small spawn setup
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            spawn_farmers = farmers[:2]
            remaining_farmers = farmers[2:]
        else:
            remaining_farmers = farmers

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All Warriors go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - attack: Warriors should attack the Dragon
        - cave: stay in Cave (not used by our strategy)
        - village: Farmers should return to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village to farm or spawn
                environment.assign_group(c, "village")
```