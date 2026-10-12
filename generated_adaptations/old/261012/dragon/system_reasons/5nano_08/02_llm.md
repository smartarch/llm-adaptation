Reasoning and adaptation strategy

Goal recap:
- Kill the Dragon as fast as possible.
- Warriors must go to the Cave and attack the Dragon.
- Farmers must stay in the Village (but can farm to produce wheat and help spawn more villagers).
- We should spawn both new Farmers and new Warriors to boost DPS.
- The Dragon should be attacked at least once in the first 15 steps.
- If all villagers die, we lose. We should keep some villagers alive and leverage spawns to maintain numbers.
- Spawn rules: in the Village, for every two villagers assigned to a spawn group and a wheat threshold, one new villager of the targeted type spawns:
  - spawn farmer group: 2 villagers + 10 wheat -> one new Farmer
  - spawn warrior group: 2 villagers + 12 wheat -> one new Warrior

Strategy outline:
- In assign_in_village:
  - Move all Warriors to the Cave (group "cave" in village stage) so they travel to the Cave and will attack the Dragon in the cave stage.
  - Keep all Farmers in the village, but create a spawn plan that uses some Farmers to spawn more Farmers and more Warriors:
    - Use two Farmers (per spawn) plus at least 10 wheat to spawn new Farmers via the "spawn farmer" group.
    - Use two Farmers (per spawn) plus at least 12 wheat to spawn new Warriors via the "spawn warrior" group.
    - The remaining Farmers stay in the "farm" group to continue producing wheat.
  - This scheme ensures:
    - Farmers stay in the Village (satisfying the requirement).
    - Some Farmers are devoted to spawning to grow the population (early growth improves DPS later).
    - Some 2-Farmer pairs are allocated to spawning Warriors to increase DPS.
    - All Warriors are in the Village stage sent to the Cave, then in the Cave stage they will be commanded to attack in the "attack" group.
- In assign_in_cave:
  - All Warriors should be commanded to "attack" (to attack the Dragon).
  - All Farmers should go to the Village ("village") to continue farming or spawning there.
  - Any villagers already in the cave who are Farmers will be moved back to the Village, and Warriors will be kept in attack mode in the cave.
- This plan ensures:
  - The Dragon is attacked early (at least once in the first 15 steps) due to Warriors moving to the Cave and attacking.
  - A steady spawn pipeline for both Farmers and Warriors is established, increasing the chances of defeating the Dragon within 30 steps.
  - Most Warriors stay in the Cave to maximize attack potential.
  - Farmers stay in the Village, with spawns used to boost the population.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Get Wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave (to go attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among Farmers
        # Determine how many spawns we can support with current wheat and available farmers
        max_spawn_farmers = min(len(farmers) // 2, wheat // 10 if wheat >= 10 else 0)

        # Wheat left after farmer spawns
        wheat_after_farm_spawns = max(0, wheat - max_spawn_farmers * 10)

        # Remaining farmers after allocating 2 per spawn for farmers
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_spawn_farmers

        # Determine how many spawns we can support for warriors (needs 12 wheat per spawn)
        max_spawn_warriors = 0
        if wheat_after_farm_spawns >= 12 and remaining_farmers_after_farm_spawns >= 2:
            max_spawn_warriors = min( remaining_farmers_after_farm_spawns // 2,
                                      wheat_after_farm_spawns // 12 )

        spawn_farmer_count = int(max_spawn_farmers)
        spawn_warrior_count = int(max_spawn_warriors)

        # 3) Assign groups for Farmers
        # We'll assign:
        # - First 2*spawn_farmer_count farmers to "spawn farmer"
        # - Next 2*spawn_warrior_count farmers to "spawn warrior"
        # - The rest to "farm"
        total_farmers = len(farmers)
        used_for_farmers = 0

        # Assign to "spawn farmer"
        for i, c in enumerate(farmers):
            if i < 2 * spawn_farmer_count:
                environment.assign_group(c, "spawn farmer")
            elif i < 2 * spawn_farmer_count + 2 * spawn_warrior_count:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

        # 4) Farmers already assigned to "cave" are Warriors; no action needed for Farmers here

        # Note: Warriors are already moved to "cave" above. If there were any farmers left in cave by some edge case,
        # they'd be assigned to village below in assign_in_cave, but here we assume current village step had farmers in village.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, command Warriors to attack and Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # Attack the Dragon
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Return Farmers to Village
                environment.assign_group(c, "village")
            else:
                # If an unexpected type appears, default to staying in Cave
                environment.assign_group(c, "cave")
```