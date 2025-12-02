Reasoning and adaptation strategy

Goal recap:
- Kill the Dragon quickly (Dragon HP starts at 50).
- Attack the Dragon early (at least once within the first 15 steps).
- All Warriors must end up in the Cave to attack the Dragon.
- All Farmers should stay in the Village (but can farm or help spawn new villagers).
- Spawn some new Farmers and Warriors to boost numbers, increasing wheat production and damage potential.
- Keep a sizable fraction of Warriors in the Cave so they can attack; ensure at least half of the Warriors are in the Cave most of the time.
- Spawning is controlled by the special spawn groups: "spawn farmer" (needs 2 villagers in the group and 10 wheat per spawn) and "spawn warrior" (needs 2 villagers in the group and 12 wheat per spawn).

Strategy description:
- In assign_in_village (villagers in the village):
  - Move all Warriors to the Cave (they will later be assigned to attack in the cave step).
  - Keep Farmers in the Village by default (in the "farm" group) to continue producing wheat.
  - Create spawn opportunities using Farmers:
    - If there are at least 4 Farmers and at least 20 wheat, assign 4 Farmers to the "spawn farmer" group to potentially spawn up to 2 new Farmers (2 spawns per 4 villagers assuming wheat allows).
    - Else if there are at least 2 Farmers and at least 10 wheat, assign 2 Farmers to the "spawn farmer" group to spawn 1 new Farmer.
    - If there are remaining Farmers beyond those used for spawning, assign them to the "farm" group (continue farming).
  - Optionally, if there are enough Farmers left after the above, and enough wheat remains, allocate up to 2 Farmers to the "spawn warrior" group to spawn a new Warrior; this uses 12 wheat per potential Warrior spawn (again dependent on wheat in the environment). The two spawned Warriors will be produced as new Warriors and will be sent to the Cave in subsequent steps.
  - This approach tends to increase future wheat and combat capability, while keeping Farmers in Village for ongoing farming.

- In assign_in_cave (villagers in the cave):
  - All Warriors in cave should attack the Dragon: assign them to the "attack" group.
  - All Farmers in cave should return to the Village: assign them to the "village" group.
  - This satisfies: Warriors attack after moving to the cave; Farmers return to farming area.

This strategy ensures:
- The Dragon is attacked early via Warriors once they reach the cave.
- Farmers stay and farm in the Village, with spawning opportunities to grow the population (both Farmers and Warriors) to sustain combat long enough to kill the Dragon.
- At least some new Warriors and Farmers appear over time, increasing the chance to kill the Dragon.
- A majority of Warriors stay in the Cave when needed to maintain pressure, while others cycle back as Farmers spawn and retreat.

Python code (class implementation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - 'farm': stay in village and farm
        - 'cave': go to the cave (we'll move Warriors here; in cave step they attack)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Farms stay in Village by default; we'll also attempt to spawn
        # Use a simple heuristic to allocate some farmers to spawn groups depending on wheat.
        local_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        spawn_farm_group = []
        spawn_warrior_group = []
        farm_group = []

        # Decide spawn farmer group
        if len(farmers) >= 4 and local_wheat >= 20:
            spawn_farm_group = farmers[:4]
            index = 4
        elif len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_group = farmers[:2]
            index = 2
        else:
            spawn_farm_group = []
            index = 0

        # Decide spawn warrior group from remaining farmers (to satisfy "spawn warrior" constraint)
        remaining_after_farm = farmers[index:]
        if len(remaining_after_farm) >= 2 and local_wheat >= 12:
            spawn_warrior_group = remaining_after_farm[:2]
            index += 2
        else:
            spawn_warrior_group = []

        # Rest go to farming
        farm_group = farmers[index:]

        # Apply group assignments
        for c in spawn_farm_group:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_group:
            environment.assign_group(c, 'spawn warrior')
        for c in farm_group:
            environment.assign_group(c, 'farm')

        # Note: Warriors were already moved to 'cave'. Any Farmers not in spawn groups default to 'farm'.
        # The spawn groups will trigger new villagers in the environment (as per game rules).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - 'attack': Warriors attack the Dragon
        - 'cave': stay in the Cave (not used by this strategy for Warriors)
        - 'village': go back to Village (Farmers primarily)
        """
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers (and any other non-warrior) go back to Village
                environment.assign_group(c, 'village')
```