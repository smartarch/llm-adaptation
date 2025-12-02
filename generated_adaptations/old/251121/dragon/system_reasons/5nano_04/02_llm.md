Reasoning and adaptation strategy (step by step)

- Goals to satisfy:
  - All Warriors must go to the Cave and attack the Dragon.
  - All Farmers should stay in the Village (but can participate in spawning to grow the population).
  - Spawn both Farmers and Warriors to increase population and DPS, using Wheat resources.
  - The Dragon must be attacked, and at least once within the first 15 steps.
  - Keep at least half of the Warriors in the Cave so they can contribute to damage consistently.
- Observations:
  - Warriors deal more damage (3 per attack) than Farmers (1 per attack).
  - Farmers produce Wheat when farming; spawning requires specific Wheat thresholds (10 for Farmer spawn, 12 for Warrior spawn) and two villagers in the respective spawn group.
  - Spawning is driven by group membership: for each two villagers in a "spawn" group and enough Wheat, a new villager is spawned.
- Strategy outline:
  - Village stage:
    - Move all Warriors to the Cave (group "cave"); keep Farmers in the Village by default (group "farm").
    - Introduce spawn groups selectively with Farmers to seed production:
      - If there are at least 4 Farmers and Wheat >= 20: place two in "spawn farmer" and two in "spawn warrior" to generate both new Farmers and Warriors.
      - Else if there are at least 2 Farmers and Wheat >= 12: place two in "spawn warrior" to generate Warriors early.
      - Else if there are at least 2 Farmers and Wheat >= 10: place two in "spawn farmer" to generate more Farmers later.
      - Otherwise, keep Farmers in "farm" unless spawning thresholds are met.
    - This approach aims to guarantee at least some Warriors exist early enough to attack within 15 steps, while also ensuring ongoing population growth.
  - Cave stage:
    - Move all Warriors present in the Cave to the "attack" group so they actively attack the Dragon.
    - Move all Farmers present in the Cave back to "village" (effectively ensuring Farmers stay in the Village per requirements).
  - By always moving Warriors to attack when in the Cave and preserving a Farm/Spawn-based growth model for Farmers, the Dragon is attacked, and DPS from Warriors remains substantial. The spawn logic helps ensure both farmers and warriors grow, satisfying the “at least a few” spawn requirement.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: Farmers stay and farm
        - cave: Warriors move to the Cave
        - spawn farmer: two villagers in this group will spawn a new Farmer (needs 10 wheat)
        - spawn warrior: two villagers in this group will spawn a new Warrior (needs 12 wheat)
        """
        # Defaults: Farmers -> farm, Warriors -> cave
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move Warriors to cave; Farmers stay in village (farm)
        for w in warriors:
            environment.assign_group(w, "cave")
        for f in farmers:
            environment.assign_group(f, "farm")

        # Spawn strategy based on available wheat and number of farmers
        wheat = getattr(environment.farm, "wheat", 0)

        # Re-assign some farmers to spawn groups if we have enough wheat and enough farmers
        # We prioritize spawning multiple villagers when possible.
        if len(farmers) >= 4 and wheat >= 20:
            # First two farmers to spawn farmer, next two to spawn warrior
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            environment.assign_group(farmers[2], "spawn warrior")
            environment.assign_group(farmers[3], "spawn warrior")
        elif len(farmers) >= 2 and wheat >= 12:
            # Spawn two Warriors from farmers
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
        elif len(farmers) >= 2 and wheat >= 10:
            # Spawn two Farmers from farmers
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
        # If none of the conditions apply, keep default assignments (farmers in farm, warriors in cave)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - attack: Warriors attack the Dragon
        - cave: (stay in the Cave) - but to satisfy farmer requirement, Farmers go to village
        - village: Farmers go back to Village
        """
        # Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village; move them back to Village
                environment.assign_group(c, "village")
```