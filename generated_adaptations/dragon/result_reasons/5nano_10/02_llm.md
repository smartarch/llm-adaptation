Reasoning and strategy description:
- Goals alignment:
  - All Warriors should go to the Cave and then attack the Dragon. To enforce this, move all Warriors from the Village to the Cave in assign_in_village, and in assign_in_cave move Warriors to the Attack group so they actually strike the Dragon.
  - All Farmers should stay in the Village. Farmers never move to the Cave; they remain in the Village. To keep a healthy population, Farmers will be used for farming (to produce wheat) and to spawn new villagers (both Farmers and Warriors) via dedicated spawn groups.
  - Spawn mechanics: For every two villagers assigned to a spawn group and the required wheat, a new villager is spawned. We must plan spawn groups within the village considering current wheat. We use an optimization to allocate 2-villager blocks to:
    - spawn farmer: costs 10 wheat per spawn
    - spawn warrior: costs 12 wheat per spawn
    The total wheat is shared, so we compute a combination (sf, sw) of spawns that maximizes total spawns given the available wheat and the number of Farmers in village.
  - Early attack guarantee: To ensure at least one attack in the first 15 steps, we always move Warriors to the Cave in the village step; then in the cave step they are assigned to the Attack group, ensuring an attack occurs as early as possible given the presence of Warriors.
  - Population growth strategy: We spawn some Farmers and Warriors to boost DPS and survivability, while maintaining the core rule that Farmers stay in the Village. By using the best (sf, sw) combination, we maximize spawns given wheat while respecting the two-villager-per-spawn constraint.
  - Population distribution stability: All Warriors originate in the Village (then move to Cave) and all Farmers remain in the Village (though some may be allocated to spawn groups for growth). In the Cave, Farmers are sent back to the Village.

- How the strategy uses the provided interface:
  - assign_in_village:
    - Move every Warrior to the Cave (group "cave").
    - For Farmers, compute the optimal number of spawns (sf, sw) based on the current wheat and available Farmers, then assign 2*sf Farmers to "spawn farmer" and 2*sw Farmers to "spawn warrior". Remaining Farmers go to "farm" (staying in Village to farm).
  - assign_in_cave:
    - Move Warriors to "attack" (they will attack the Dragon).
    - Move Farmers to "village" (they should go back to the Village).
  - This ensures: all Warriors are in the Cave to attack, Farmers stay in Village, and spawning happens opportunistically to enlarge the force.

Python code (SmartAdaptation class):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village and are allocated to farming or spawning groups
        n_farmers = len(farmers)

        # Current wheat available for spawning (environment.farm.wheat)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We want to maximize spawns: for sf spawns of Farmer and sw spawns of Warrior
        # Constraints:
        #  - 2*sf + 2*sw <= n_farmers
        #  - 10*sf + 12*sw <= wheat
        # We search all feasible (sf, sw) pairs and pick the one with maximum total spawns (sf+sw),
        # breaking ties arbitrarily (preferring more spawns).
        max_sf = min(n_farmers // 2, wheat // 10) if n_farmers >= 2 else 0
        best_sf, best_sw = 0, 0
        best_score = -1

        for sf in range(0, max_sf + 1):
            remaining_farmers = n_farmers - 2 * sf
            remaining_wheat = wheat - 10 * sf
            if remaining_wheat < 0:
                continue
            max_sw = min(remaining_farmers // 2, remaining_wheat // 12) if remaining_farmers >= 2 else 0
            if max_sw < 0:
                continue
            # We want to maximize spawns count
            sw = max_sw
            score = sf + sw
            if score > best_score:
                best_score = score
                best_sf, best_sw = sf, sw

        # Assign farmers to the spawn groups first, then remaining to farming
        idx = 0
        # To ensure deterministic behavior, keep an ordered list
        farmers_list = farmers[:]

        # Spawn farmer: 2 villagers per spawn
        for _ in range(2 * best_sf):
            if idx < len(farmers_list):
                environment.assign_group(farmers_list[idx], "spawn farmer")
                idx += 1

        # Spawn warrior: 2 villagers per spawn
        for _ in range(2 * best_sw):
            if idx < len(farmers_list):
                environment.assign_group(farmers_list[idx], "spawn warrior")
                idx += 1

        # Remaining farmers stay in farming group (in Village)
        while idx < len(farmers_list):
            environment.assign_group(farmers_list[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```