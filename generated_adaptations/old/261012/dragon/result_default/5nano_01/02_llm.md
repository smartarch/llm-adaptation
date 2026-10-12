Reasoning and adaptation strategy

Task analysis:
- We control villagers split between a Village and a Cave.
- Warriors deal more damage in cave combat; Farmers are essential for farming and spawning more villagers (to accelerate recruitment and DPS).
- Spawning new villagers uses two villagers in a spawn group plus a wheat cost (10 for Farmer, 12 for Warrior).
- All Warriors should eventually go to the Cave to attack the Dragon; Farmers should stay in the Village unless spawning new villagers.
- The Dragon starts with 50 HP; the goal is to kill it within 30 steps.

Strategy (overview):
- In assign_in_village (Village phase):
  - Move all Warriors to the Cave (group "cave" for the Village phase means they go to the cave).
  - Keep Farmers in the Village by default (group "farm" for farming).
  - Introduce a spawning plan for Farmers and Warriors using two special groups: "spawn farmer" and "spawn warrior".
  - Use the available wheat from the Farm to decide how many spawns can occur this step, adhering to the constraints:
    - Each spawn event requires 2 villagers assigned to the spawn group and 10 wheat (spawn Farmer) or 12 wheat (spawn Warrior).
    - For a single step, you can spawn multiple villagers as long as there are enough villagers to form pairs and enough wheat.
  - Spawn allocation logic (greedy, but safe):
    - First, allocate as many 2-villager pairs to spawn Farmers as possible given wheat and available Farmers.
    - Then allocate as many 2-villager pairs to spawn Warriors with the remaining Farmers and remaining wheat.
    - The remaining Farmers stay in Village to farm.

  Rationale:
  - Spawning is constrained by wheat and by two-villager-per-spawn. Since Wheat is produced by farming, it makes sense to first allocate some Farmers to farming and to use the Wheat to spawn additional Farmers (which increases Wheat production and population for future steps). After that, spawn Warriors if Wheat allows, to increase damage output.
  - All Warriors go to the Cave to attack; Farmers either farm or participate in spawning.

- In assign_in_cave (Cave phase):
  - All Warriors in the Cave should be assigned to the "attack" group (to fight the Dragon).
  - All Farmers currently in the Cave should go back to the Village (group "village"), since Farmers should stay in the Village for farming/spawning.

- Implementation details:
  - Components expose attributes: role ("Farmer" or "Warrior") and hp. These are read-only for grouping decisions.
  - The Dragon and Farm wheat state are accessible via environment.dragon.hp and environment.farm.wheat, but we only use environment.farm.wheat to determine spawning capacity.
  - Group IDs to use exactly as required: "farm", "cave", "spawn farmer", "spawn warrior" in village; "attack", "cave", "village" in cave.
  - All assignments must call environment.assign_group(component, group_id).

Python code (class SmartAdaptation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In Village: move Warriors to cave, keep Farmers here, but optionally spawn new villagers.
        # First, assign all Warriors to the cave group (to go attack later).
        farmers = []
        warrior_count = 0

        for comp in components:
            role = str(getattr(comp, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(comp, "cave")
                warrior_count += 1
            else:  # assume Farmer
                farmers.append(comp)

        # Determine available wheat (default 0 if farm not present)
        wheat_here = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            wheat_here = getattr(farm, "wheat", 0)

        # Spawning plan:
        # - We can spawn at most floor(len(farmers) / 2) Farmers (two per spawn)
        # - We can spawn at most floor(wheat_here / 10) Farmers (10 wheat per Farmer-spawn)
        # - Then with remaining farmers (two-villager pairs) we can spawn Warriors (12 wheat per Warrior-spawn)
        spawns_farmers = 0
        spawns_warriors = 0

        n_farmers = len(farmers)

        if n_farmers >= 2 and wheat_here >= 10:
            max_by_villagers = n_farmers // 2
            max_by_wheat = wheat_here // 10
            spawns_farmers = min(max_by_villagers, max_by_wheat)

        # Update remaining wheat after farmer spawns
        wheat_after_farm_spawns = wheat_here - (spawns_farmers * 10)
        remaining_farmers_for_warrior_spawns = n_farmers - (2 * spawns_farmers)

        if remaining_farmers_for_warrior_spawns >= 2 and wheat_after_farm_spawns >= 12:
            max_by_villagers = remaining_farmers_for_warrior_spawns // 2
            max_by_wheat = wheat_after_farm_spawns // 12
            spawns_warriors = min(max_by_villagers, max_by_wheat)

        # Assign farmers to proper spawn groups or farming
        total_farmers = len(farmers)
        for idx, comp in enumerate(farmers):
            if idx < 2 * spawns_farmers:
                environment.assign_group(comp, "spawn farmer")
            elif idx < 2 * spawns_farmers + 2 * spawns_warriors:
                environment.assign_group(comp, "spawn warrior")
            else:
                environment.assign_group(comp, "farm")

        # Note: If no farmers exist, nothing further to do.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack the Dragon; Farmers should go back to Village.
        for comp in components:
            role = str(getattr(comp, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(comp, "attack")
            else:  # Farmer
                environment.assign_group(comp, "village")
```