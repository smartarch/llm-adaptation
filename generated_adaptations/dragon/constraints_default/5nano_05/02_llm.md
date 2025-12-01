Reasoning and adaptation strategy

Task understanding:
- Warriors should always go to the Cave and attack the Dragon.
- Farmers should stay in the Village to farm and/or participate in spawning new villagers (Farmers and Warriors are both needed for spawning).
- Spawning rules: In the Village, for every two villagers assigned to a spawn group and enough wheat, a new villager is spawned:
  - spawn farmer needs 10 wheat per 2 villagers assigned.
  - spawn warrior needs 12 wheat per 2 villagers assigned.
- The Dragon can retaliate; we aim to keep enough villagers alive while producing wheat and spawning new villagers to sustain the attack.
- All Warriors in the Village should be moved to the Cave and Attack in the Cave phase.

Strategy description:
- In assign_in_village:
  - Move all Warriors to the cave (to attack the Dragon as soon as possible).
  - Keep Farmers in the Village for farming or spawning.
  - Opportunistically use a small, deterministic spawning plan:
    - If there is at least 10 wheat, designate up to 2 Farmers to the "spawn farmer" group to attempt to spawn a new Farmer.
    - If there is at least 12 wheat and there are at least 2 Farmers not already in a spawn farmer group, designate 2 of them to the "spawn warrior" group to attempt to spawn a new Warrior.
    - The remaining Farmers stay in the "farm" group to continue farming.
  - This approach provides a simple, incremental growth of villagers while maintaining farming to support wheat production and providing Warriors to reinforce the attack over time.
- In assign_in_cave:
  - Warriors in the Cave are assigned to "attack" (to fight the Dragon).
  - Farmers in the Cave are assigned to "village" (they should return to the Village to farm/spawn).

This strategy ensures:
- All Warriors head to the Cave to maximize DPS on the Dragon.
- Farmers stay in the Village to farm and spawn new villagers when wheat allows.
- Spawns are driven by wheat availability and limited to small, manageable numbers to avoid starving farming progress.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Village into:
        - farm: stay in Village and farm
        - cave: go to Cave
        - spawn farmer: for every 2 villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every 2 villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village by default (farmable)
        # We'll decide how many to allocate to spawn groups based on available wheat.
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 3) Spawn planning (limited and deterministic)
        # Calculate how many farmers can be sent to spawn farmer (max 2)
        spawn_farmer_count = 0
        if wheat >= 10:
            spawn_farmer_count = min(2, len(farmers))

        # Assign first batch to "spawn farmer"
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")

        # Remaining farmers not assigned to spawn farmer
        remaining_for_warrior = farmers[spawn_farmer_count:]

        # Calculate if we can spawn warriors: need at least 2 villagers in group and at least 12 wheat
        spawn_warrior_count = 0
        if wheat >= 12 and len(remaining_for_warrior) >= 2:
            # Spawn up to 2 Warriors (requires 2 villagers in the group)
            spawn_warrior_count = 2

        # Assign to "spawn warrior" if possible
        for idx in range(spawn_warrior_count):
            environment.assign_group(remaining_for_warrior[idx], "spawn warrior")

        # Remaining farmers go to "farm"
        for f in remaining_for_warrior[spawn_warrior_count:]:
            environment.assign_group(f, "farm")

        # Note: Any farmers not explicitly assigned here are covered by the above logic.
        # If a farmer list is empty, nothing to do for farmers.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, split villagers as:
        - attack: Warriors
        - cave: Stay in Cave (not used by our strategy, but keep for completeness)
        - village: Farmers go back to Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to the Village
                environment.assign_group(c, "village")
```