Reasoning and strategy description

Goal alignment and constraints
- All Warriors should go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but we can use a small portion of Farmers to seed spawns while staying effectively in the Village).
- We want to attack early (at least once in the first 15 steps) and keep the Dragon under pressure to win within 30 steps.
- We should spawn some new Farmers and Warriors: spawns require at least two villagers in the corresponding spawn group and a wheat cost (10 wheat for a Farmer, 12 wheat for a Warrior). Spawning consumes wheat from the Farm.

Strategy overview
- In the Village:
  - Move all existing Warriors to the Cave (they will be processed in the Cave step as attackers).
  - Keep Farmers in the Village as Farmers (for farming) but optionally use a small seed for spawning: if there are enough Farmers and enough wheat, temporarily assign some Farmers to the spawn groups to generate new villagers.
  - Spawn plan:
    - If there are at least 4 Farmers and at least 22 wheat, allocate 2 Farmers to "spawn farmer" (10 wheat per spawn -> one Farmer spawned) and 2 Farmers to "spawn warrior" (12 wheat per spawn -> one Warrior spawned). This makes both a new Farmer and a new Warrior available while still keeping most Farmers in the Village.
    - Else if there are at least 2 Farmers and at least 10 wheat, allocate 2 Farmers to "spawn farmer" to spawn at least one additional Farmer.
    - Otherwise, do not spawn.
- In the Cave:
  - Move all Farmers back to the Village (group "village") and assign all Warriors to "attack" (to attack the Dragon).
  - This ensures all Warriors attack the Dragon once they have arrived, meeting the requirement that all Warriors should attack after moving to the Cave and that at least half (indeed all) are available to attack.

Rationale
- This strategy guarantees early Dragon aggression by ensuring Warriors are sent to the Cave quickly and assigned to attack in the cave. If there are no Warriors initially, the spawning mechanism is attempted (when wheat and Farmer count allow) to produce at least one Warrior to attack early.
- Farmers mostly stay in the Village to farm wheat, increasing the wheat pool to enable spawning. The spawning steps are kept minimal to avoid depleting Farmer presence unexpectedly, but still provide additional Warriors and Farmers to improve DPS against the Dragon.
- The spawning rules are implemented within the constraints: you need two villagers in the spawn group and the required wheat to trigger a spawn. We use simple, conservative spawning logic to ensure at least some spawns happen when resources permit.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: Farmers stay in Village as 'farm', Warriors go to Cave as 'cave'
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Attempt spawning based on available wheat and number of farmers
        wheat = getattr(environment.farm, "wheat", 0)

        # Case 1: If we have enough farmers and wheat to seed both a farmer and a warrior
        if len(farmers) >= 4 and wheat >= 22:
            # Use first two farmers to spawn a Farmer, next two to spawn a Warrior
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            for c in farmers[2:4]:
                environment.assign_group(c, "spawn warrior")

        # Case 2: If we don't have enough for both, try to spawn at least one Farmer
        elif len(farmers) >= 2 and wheat >= 10:
            # Use first two farmers to spawn a Farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")

        # If there are no spawns possible, farmers remain in 'farm' and Warriors in 'cave'
        # The environment will handle the actual spawning based on these group assignments.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack the Dragon; Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```