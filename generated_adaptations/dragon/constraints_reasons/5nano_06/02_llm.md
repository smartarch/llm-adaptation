Strategy and reasoning

Goal recap:
- Kill the Dragon as fast as possible.
- All Warriors must go to the Cave and attack the Dragon.
- All Farmers must stay in the Village (but they can also participate in spawning actions).
- Spawn mechanics: assign villagers to "spawn farmer" (needs 2 villagers in that group and at least 10 wheat) or to "spawn warrior" (needs 2 villagers in that group and at least 12 wheat) to create new villagers of the respective type.
- Early attack: ensure the Dragon is attacked within the first 15 steps.
- Wheat is produced by Farmers when farming; we should keep some farmers farming to accumulate wheat for spawns.
- Spawned villagers add to DPS later; we should spawn both Farmers and Warriors to improve odds of killing the Dragon.

Proposed adaptation strategy (what to do and why):
- In the village:
  - Move all Warriors to the cave to prepare for an early attack (they will be moved again in the cave step to attack).
  - Keep Farmers in the Village by default (to farm and produce wheat).
  - If enough wheat is available, use a small, controlled spawning plan:
    - If there are at least 2 Farmers and wheat >= 10, assign 2 Farmers to "spawn farmer" to spawn 1 new Farmer (per 2 villagers + 10 wheat).
    - If there are at least 4 Farmers in total and wheat is still high (>= 12), assign another 2 Farmers to "spawn warrior" to spawn 1 new Warrior (per 2 villagers + 12 wheat). This helps quickly boost DPS without starving the village of workers.
  - This keeps enough Farmers to produce wheat for spawning and adds a small number of new villagers to increase DPS.
- In the cave:
  - Move all Farmers back to the Village (to keep farming wheat) and keep Warriors in the Cave to attack.
  - Specifically assign Warriors to the "attack" group so they start attacking the Dragon as soon as they are in the Cave.
  - Farmers should go to the Village (not stay in the Cave) to keep wheat production going.

This approach:
- Ensures immediate Dragon exposure by sending Warriors to the cave to attack early.
- Maintains a wheat-producing base by keeping Farmers in the Village (and spawning more villagers when resources permit).
- Spawns a small number of new Farmers and Warriors to increase DPS with minimal disruption to wheat production.
- Keeps the majority of Warriors ready to attack (ensuring "at least half of the warriors should be in the Cave most of the time" by design since Warriors go to cave in village and then attack in cave).

Implementation plan:
- assign_in_village:
  - Classify villagers by role.
  - Assign all Warriors to "cave" (they will move to the cave this step).
  - Assign all Farmers to "farm" by default.
  - If possible, spawn new villagers:
    - If there are at least 2 Farmers and wheat >= 10: move two Farmers to "spawn farmer" (spawn 1 new Farmer).
    - If there are at least 4 Farmers (including those not used above) and wheat >= 12: move two more Farmers to "spawn warrior" (spawn 1 new Warrior).
- assign_in_cave:
  - Move all Warriors to "attack" group.
  - Move all Farmers to "village" group (they go back to the Village).

Code implementation (Python):

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the Cave (prepare for attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) All Farmers should stay in the Village by default (farm)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Spawn logic (spawn a few new villagers if resources allow)
        # Current wheat in the farm
        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We'll try to spawn at most two villagers per update to stay conservative
        # First, attempt to spawn a Farmer (needs 2 villagers in "spawn farmer" and >= 10 wheat)
        if len(farmers) >= 2 and current_wheat >= 10:
            to_spawn_farmers = farmers[:2]  # take first two farmers to spawn
            for c in to_spawn_farmers:
                environment.assign_group(c, "spawn farmer")
            # After triggering a farmer spawn, wheat will be consumed by the environment;
            # attempt to spawn a Warrior if resources allow and we have more farmers left
            # Check remaining farmers (excluding those just assigned to spawn farmer)
            remaining_after_farm_spawn = farmers[2:]
            if len(remaining_after_farm_spawn) >= 2 and current_wheat >= 12:
                to_spawn_warriors = remaining_after_farm_spawn[:2]
                for c in to_spawn_warriors:
                    environment.assign_group(c, "spawn warrior")
        else:
            # If not enough to spawn a farmer, try spawning a Warrior directly if resources allow
            if len(farmers) >= 2 and current_wheat >= 12:
                to_spawn_warriors = farmers[:2]
                for c in to_spawn_warriors:
                    environment.assign_group(c, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep them in cave if role is unknown
                environment.assign_group(c, "cave")
```