Reasoning and adaptation strategy

Task understanding:
- We must partition villagers into groups differently depending on whether they’re in the Village or in the Cave.
- Warriors should end up in the Cave and attack the Dragon as soon as possible.
- Farmers should stay in the Village to farm or to trigger spawning of new villagers (Farmers and Warriors).
- Spawning rules: For every two villagers assigned to "spawn farmer" and 10 wheat, a new Farmer is spawned. For every two villagers assigned to "spawn warrior" and 12 wheat, a new Warrior is spawned.
- We can observe current wheat via environment.farm.wheat and spawn using the two designated groups. Spawning consumes wheat but the exact spawning mechanism is handled by the environment; our job is to assign the needed villagers to the spawn groups.
- In the Cave, Warriors should attack (group "attack"), Farmers should move back to the Village (group "village"). Within the Cave, there is no reason to keep Farmers stationed there.

Strategy outline:
- In assign_in_village (Village):
  - Move all Warriors to the Cave by assigning them to the "cave" group.
  - For Farmers, attempt to spawn new villagers to increase headcount:
    - First, allocate as many pairs of Farmers to the "spawn farmer" group as possible given available wheat (10 per spawn) and at least two Farmers per spawn.
    - Then, with the remaining Farmers, attempt to spawn Warriors using the "spawn warrior" group (needs 12 wheat and two villagers per spawn).
  - Any Farmers not used for spawning are assigned to the "farm" group to keep farming in the Village.
  - Ensure each villager is assigned to exactly one group.
- In assign_in_cave (Cave):
  - All Warriors in the Cave should be assigned to "attack" to target the Dragon.
  - All Farmers in the Cave should be moved back to the Village by assigning them to "village".
  - No one should remain in the "cave" group unless they are Warriors not yet ready to attack (we enforce attack for all Warriors to simplify the strategy).

Notes:
- The above strategy honors the requirement that all Warriors should go to the Cave and attack; all Farmers stay in the Village for farming or spawning.
- Spawning relies on wheat and available farmers; we implement a deterministic, straightforward allocation to maximize spawns given current Wheat and Farmer pool.

Code implementation:
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
        # Track available wheat in the Farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # We will work with a local copy of the farmer pool
        remaining_farmers = farmers_indices.copy()

        # Spawn Farmers: 2 farmers + 10 wheat -> 1 Farmer spawned
        while len(remaining_farmers) >= 2 and wheat >= 10:
            idx1 = remaining_farmers.pop(0)
            idx2 = remaining_farmers.pop(0)
            assigned[idx1] = SPAWN_FARMER_GROUP
            assigned[idx2] = SPAWN_FARMER_GROUP
            wheat -= 10
            # A new Farmer will be spawned by the environment based on this assignment

        # Spawn Warriors: 2 villagers + 12 wheat -> 1 Warrior spawned
        while len(remaining_farmers) >= 2 and wheat >= 12:
            idx1 = remaining_farmers.pop(0)
            idx2 = remaining_farmers.pop(0)
            assigned[idx1] = SPAWN_WARRIOR_GROUP
            assigned[idx2] = SPAWN_WARRIOR_GROUP
            wheat -= 12
            # A new Warrior will be spawned by the environment based on this assignment

        # 3) Remaining Farmers go to Farm group
        for idx in remaining_farmers:
            assigned[idx] = FARM_GROUP

        # 4) Assign any villagers not yet assigned (fallback safety)
        for idx in range(len(components)):
            if idx not in assigned:
                # Default to farming if Farmer-like, otherwise to cave back to Village
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