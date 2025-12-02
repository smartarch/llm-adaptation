Reasoning and strategy description

Goal alignment
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in the Village, where they can farm to accumulate wheat and optionally participate in spawning.
- Spawn mechanisms exist to grow the village: spawn farmer and spawn warrior groups. For every two villagers assigned to a spawn group and given enough wheat, a new villager is spawned (a Farmer for the spawn farmer group, a Warrior for the spawn warrior group).
- We need to ensure the Dragon is attacked, and we want to attack early (within the first 15 steps). We also want to keep at least half of the Warriors in the Cave to maximize attack potential.

Strategy overview
- Village phase (assign_in_village):
  - Move all Warriors to the Cave (group "cave") so they can later attack.
  - Keep Farmers in the Village by default (group "farm").
  - Use wheat-aware spawning to create a few extra Farmers and a few extra Warriors over time:
    - If there are at least 2 Farmers and the Farm has at least 10 wheat, assign two Farmers to the "spawn farmer" group to enable spawning of new Farmers.
    - If there are enough remaining Farmers and the Farm has at least 12 wheat, assign two Farmers to the "spawn warrior" group to enable spawning of new Warriors.
  - This approach ensures:
    - Warriors will be in the Cave and ready to attack.
    - Farmers stay in the Village to farm, while some are sacrificed temporarily to spawn additional villagers, increasing long-term Dragon-killing potential.
    - We always maintain the possibility and probability of spawning more villagers as wheat accumulates.

- Cave phase (assign_in_cave):
  - Move all Warriors to the "attack" group so they actively attack the Dragon.
  - Move all Farmers to the "village" group, sending them back to the Village to continue farming or waiting for spawning opportunities.
  - This keeps at least half of the Warriors in the Cave as attackers and ensures an attack occurs early (as soon as Warriors are in the Cave).

Implementation notes
- The adaptation uses environmental wheat counts to decide whether to enable the spawn groups.
- The code assigns each component to exactly one group as required.
- The code ensures that there will be attacking Warriors in the Cave when available, supporting the early attack requirement.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - farm: Farmers stay in the Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: allocate some Farmers to enable spawning of new Farmers
        - spawn warrior: allocate some Farmers to enable spawning of new Warriors
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default moves
        to_farm = []
        to_spawn_farmer = []
        to_spawn_warrior = []
        to_cave = []

        # All Warriors should head to the Cave to attack
        to_cave.extend(warriors)

        # Farmers stay in Village by default
        remaining_farmers = list(farmers)

        # Wheat available for spawning logic
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Try to spawn farmers if possible (need >=2 farmers and >=10 wheat)
        if len(remaining_farmers) >= 2 and wheat >= 10:
            to_spawn_farmer = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]
        # Try to spawn warriors if possible (need >=2 farmers remaining and >=12 wheat)
        if len(remaining_farmers) >= 2 and wheat >= 12:
            to_spawn_warrior = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]

        # The rest stay in farm
        to_farm = remaining_farmers

        # Assign groups
        for c in to_farm:
            environment.assign_group(c, "farm")
        for c in to_spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave (not used in this strategy, but kept for completeness)
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")
```