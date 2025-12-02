Reasoning and adaptation strategy:
- Objective: Kill the Dragon as fast as possible within 30 steps.
- Core policy: All Warriors should work in the Cave to attack the Dragon; Farmers should stay in the Village to farm wheat and to spawn more villagers when resources allow.
- Spawning logic: Use two villagers together with the required wheat to spawn a new villager of the desired type. Specifically:
  - Spawn Farmer: need 2 Farmers in the "spawn farmer" group and 10 wheat in the Farm. Each pair yields one new Farmer.
  - Spawn Warrior: need 2 Farmers in the "spawn warrior" group and 12 wheat in the Farm. Each pair yields one new Warrior.
- Wheat management: Farmers generate wheat when farming (Farm group). We should allocate some farmers to spawn groups based on current wheat, and remaining farmers to farming, to maximize wheat availability for spawns and future farming damage capacity.
- Practical allocation in assign_in_village:
  - All Warriors go to the cave (group "cave" in village) so they will eventually attack in assign_in_cave.
  - Partition Farmers into three subgroups:
    - spawn farmer: 2-farmer chunks, consuming 10 wheat per spawn
    - spawn warrior: 2-farmer chunks, consuming 12 wheat per spawn
    - farm: the rest, to keep producing wheat (5 wheat per farmer per farming action)
  - The order of assignment is deterministic based on the current list order, to ensure reproducibility.
- In assign_in_cave:
  - All Warriors should attack the Dragon (group "attack").
  - Farmers should stay in the Village (group "village").
  - The "cave" group can be left empty in this step, since Warriors are moved to attack.

This strategy keeps the army growth tied to wheat production and uses spawning to scale the force while ensuring the Dragon is continually pressured by warriors in the cave.

Python code (single code block):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (to join the attacking warriors)
        - "spawn farmer": form pairs to spawn new Farmers (needs 10 wheat per spawn)
        - "spawn warrior": form pairs to spawn new Warriors (needs 12 wheat per spawn)
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (eventually to attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Farmers logic: split into spawn groups and farming
        total_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Number of farmer-spawns we can attempt (each spawn requires 2 Farmers and 10 wheat)
        spawn_farmers_pairs = min(len(farmers) // 2, total_wheat // 10)

        idx = 0
        # Assign first 2*spawn_farmers_pairs Farmers to "spawn farmer"
        for _ in range(spawn_farmers_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Update remaining wheat after farmer spawns
        remaining_wheat = total_wheat - spawn_farmers_pairs * 10

        # Remaining Farmers available
        remaining_farmers = len(farmers) - spawn_farmers_pairs * 2

        # Number of additional spawns we can attempt for Warriors using remaining wheat
        spawn_warriors_pairs = min(remaining_farmers // 2, remaining_wheat // 12)

        for _ in range(spawn_warriors_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # The rest of the farmers go to farming
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: If there are no farmers, or after spawning some, remaining farmers
        # are assigned to "farm" by the loop above (or none if none exist).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave (unused in this policy)
        - "village": Go to the Village (Farmers return to farming)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```