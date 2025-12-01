Reasoning and updated adaptation strategy

What failed and why:
- The tests expect the strategy to actively spawn new Warriors (and Farmers) to increase the chance of killing the Dragon. My previous approach prioritized spawning Farmers first after moving Warriors to the Cave, which could lead to situations where no Warriors are spawned when wheat is limited or farmers are insufficient for both spawn types.
- To improve, I updated the Village-side logic to:
  - Always move all Warriors to the Cave (as required).
  - First allocate as many Warrior spawns as possible given the current wheat and the number of Farmers available (2 Farmers per Warrior spawn, 12 wheat per spawn). This ensures we generate new Warriors when possible.
  - Then allocate as many Farmer spawns as possible with the remaining Farmers and remaining wheat (2 Farmers per Farmer spawn, 10 wheat per spawn).
  - Any remaining Farmers stay in farming or are allocated to the appropriate farming group.
- The Cave logic remains: Warriors attack the Dragon, Farmers return to the Village, and others stay in the Cave.

What changed:
- In assign_in_village, I re-ordered and clarified the spawning logic:
  - Determine number of Warrior spawns first (based on available Farmers and wheat).
  - Then determine number of Farmer spawns with the remaining Farmers and wheat.
  - Ensure every Villager is assigned exactly once (no leftovers), and default fallbacks are minimized.

Now, the code implements the improved spawning-first strategy and keeps all Warriors in the Cave attacking the Dragon.

Code:
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group IDs to use (exact names required)
        FARM_GROUP = "farm"
        CAVE_GROUP = "cave"
        SPAWN_FARMER_GROUP = "spawn farmer"
        SPAWN_WARRIOR_GROUP = "spawn warrior"

        # Collect indices by role in the Village
        farmers_indices = []
        warriors_indices = []
        for idx, comp in enumerate(components):
            if comp.role == "Farmer":
                farmers_indices.append(idx)
            elif comp.role == "Warrior":
                warriors_indices.append(idx)
            else:
                # Unknown role; default to farming
                farmers_indices.append(idx)

        assigned = {}

        # 1) Move all Warriors to the Cave (they will attack later)
        for idx in warriors_indices:
            assigned[idx] = CAVE_GROUP  # "cave"

        # 2) Spawn logic with Farmers
        # Get current wheat amount from the Farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Work with a local copy of the farmer pool
        remaining_farmers = farmers_indices.copy()

        # Warrior spawns: 2 villagers + 12 wheat -> 1 Warrior spawned
        # Use as many pairs of farmers as possible given wheat
        max_warrior_spawns = min(len(remaining_farmers) // 2, wheat // 12)

        for _ in range(max_warrior_spawns):
            idx1 = remaining_farmers.pop(0)
            idx2 = remaining_farmers.pop(0)
            assigned[idx1] = SPAWN_WARRIOR_GROUP
            assigned[idx2] = SPAWN_WARRIOR_GROUP
            wheat -= 12

        # Farmer spawns: 2 villagers + 10 wheat -> 1 Farmer spawned
        max_farmer_spawns = min(len(remaining_farmers) // 2, wheat // 10)

        for _ in range(max_farmer_spawns):
            idx1 = remaining_farmers.pop(0)
            idx2 = remaining_farmers.pop(0)
            assigned[idx1] = SPAWN_FARMER_GROUP
            assigned[idx2] = SPAWN_FARMER_GROUP
            wheat -= 10

        # 3) Remaining Farmers go to Farm group
        for idx in remaining_farmers:
            assigned[idx] = FARM_GROUP

        # 4) Assign any villagers not yet assigned (safety fallback)
        for idx in range(len(components)):
            if idx not in assigned:
                if components[idx].role == "Farmer":
                    assigned[idx] = FARM_GROUP
                else:
                    assigned[idx] = CAVE_GROUP

        # Apply assignments
        for idx, comp in enumerate(components):
            environment.assign_group(comp, assigned.get(idx, FARM_GROUP))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group IDs to use (exact names required)
        ATTACK_GROUP = "attack"
        CAVE_GROUP = "cave"
        VILLAGE_GROUP = "village"

        for comp in components:
            if comp.role == "Warrior":
                environment.assign_group(comp, ATTACK_GROUP)
            elif comp.role == "Farmer":
                # Farmers should return to Village
                environment.assign_group(comp, VILLAGE_GROUP)
            else:
                # Fallback: keep in Cave
                environment.assign_group(comp, CAVE_GROUP)
```