Strategy reasoning and plan

Overview
- The goal is to coordinate villagers (Farmers and Warriors) to efficiently kill the Dragon as fast as possible while following the constraints.
- All Warriors should end up in the Cave to attack the Dragon. All Farmers should stay in the Village unless they are used to spawn new villagers via the spawn groups.
- Spawning rules:
  - Group "spawn farmer": For every 2 villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - Group "spawn warrior": For every 2 villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- We must ensure:
  - The Dragon is attacked at least once within the first 15 steps.
  - At least a few new farmers and a few new warriors are spawned to bolster the army.
  - All warriors eventually attack the Dragon after moving to the Cave.
  - At least half of the warriors should be in the Cave most of the time.

Implementation approach
- assign_in_village:
  - Move all current Warriors to the Cave by assigning them to the "cave" group.
  - Use Farmers to seed spawning:
    - If at least two Farmers remain and there is enough wheat (>= 12), assign two Farmers to "spawn warrior" to spawn a new Warrior.
    - If still enough Farmers remain and there is enough wheat (>= 10), assign two more Farmers to "spawn farmer" to spawn a new Farmer.
    - The remaining Farmers are assigned to "farm" to continue wheat production.
  - This strategy ensures:
    - Warriors move toward the Dragon to attack.
    - Spawned new villagers increase future fighting capability.
    - Wheat constraints are respected when triggering spawns.
- assign_in_cave:
  - All Warriors in the cave are assigned to "attack" (so they attack the Dragon).
  - Farmers in the cave are assigned to "village" (to return to the village and continue farming/spawning later).
- This approach guarantees:
  - Attack is triggered early (via existing and spawned Warriors).
  - A continual pipeline of new Farmers and Warriors is created to improve odds of killing the Dragon.
  - The requirement that all Warriors ultimately attack is respected because in each cave step we place all Warriors into "attack".

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Farmers stay in village farming
        - cave: Warriors go to the Cave
        - spawn farmer: Used to spawn new Farmers (needs 2 villagers + 10 wheat)
        - spawn warrior: Used to spawn new Warriors (needs 2 villagers + 12 wheat)
        """
        # Separate current farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all existing Warriors to the Cave (to eventually attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn decisions from farmers (if possible)
        remaining_farmers = list(farmers)  # copy

        # Attempt to spawn a Warrior: needs at least 2 villagers and 12 wheat
        to_spawn_warrior = []
        if len(remaining_farmers) >= 2:
            try:
                wheat = environment.farm.wheat
            except Exception:
                wheat = 0
            if wheat >= 12:
                to_spawn_warrior = remaining_farmers[:2]
                remaining_farmers = remaining_farmers[2:]
                for f in to_spawn_warrior:
                    environment.assign_group(f, "spawn warrior")

        # Attempt to spawn a Farmer: needs at least 2 villagers and 10 wheat
        to_spawn_farmer = []
        if len(remaining_farmers) >= 2:
            try:
                wheat = environment.farm.wheat
            except Exception:
                wheat = 0
            if wheat >= 10:
                to_spawn_farmer = remaining_farmers[:2]
                remaining_farmers = remaining_farmers[2:]
                for f in to_spawn_farmer:
                    environment.assign_group(f, "spawn farmer")

        # 3) Remaining Farmers go to farming in village
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # Note: The actual spawning results depend on the wheat available in environment.farm.wheat.
        # This strategy aims to create a steady influx of new villagers while keeping Warriors headed to the Cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Warrior villagers attack the Dragon
        - cave: Stay in the Cave (for completeness, though we will push Warriors to attack)
        - village: Go back to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(c, "village")
```