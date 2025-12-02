Strategy reasoning and plan

- Objective: Kill the Dragon as fast as possible while keeping villagers alive. Warriors are stronger in combat, but all Warriors must stay in the Cave to attack the Dragon. Farmers stay in the Village to farm and to spawn new villagers (both Farmers and Warriors are useful for long-term growth). Spawning consumes wheat and requires two villagers assigned to the corresponding spawn group.

- High-level strategy:
  - In the Village:
    - All existing Warriors are sent to the Cave to attack the Dragon (as required).
    - All Farmers stay in the Village. To balance immediate needs with long-term growth, some Farmers will be allocated to spawn new Farmers and some to spawn new Warriors, depending on available wheat.
      - Spawn Farmer: For every 2 Farmers assigned to this group and 10 wheat, a new Farmer is spawned. We implement this by allocating 2*k_farm Farmers to the "spawn farmer" group, where k_farm is the maximum number of spawns allowed given current wheat and number of Farmers.
      - The rest of Farmers go to the "farm" group to continue producing wheat.
      - Spawn Warrior: For every 2 Farmers assigned to this group and 12 wheat, a new Warrior is spawned. We allocate 2*k_war Farmers to the "spawn warrior" group (from the remaining Farmers after the spawn-farmer allocation), limited by remaining wheat (after potential farm spawns) and by the number of available Farmers (in pairs).
    - This approach ensures:
      - Warriors are ready in the Cave to attack.
      - Farmers continue to farm unless there is wheat to spare to spawn more villagers, providing a balanced growth strategy.
  - In the Cave:
    - All Warriors are assigned to the "attack" group (to fight the Dragon).
    - All Farmers are assigned to the "village" group to go back to the Village (they should not stay in the Cave or the "cave" group per requirements).

- Important notes:
  - Each step we explicitly re-assign every component to exactly one group (even if it’s the same as last step) to satisfy the constraint about “continue performing the same action” requiring explicit re-assignment.
  - Spawning is driven by current wheat in the Farm environment (environment.farm.wheat). We compute the maximum possible spawns given wheat and the number of villagers we allocate to each spawn group.

- Implementation outline:
  - assign_in_village:
    - Gather farmers and warriors from components.
    - Assign all warriors to group "cave".
    - Compute k_farm = min(len(farmers)//2, wheat//10).
    - Assign first 2*k_farm farmers to "spawn farmer".
    - Remaining farmers form the pool farm_candidates.
    - Compute k_war = min(len(farm_candidates)//2, (wheat - 10*k_farm)//12).
    - Assign first 2*k_war of farm_candidates to "spawn warrior".
    - Assign the rest to "farm".
  - assign_in_cave:
    - Warriors -> "attack".
    - Farmers -> "village".

- This strategy honors the constraint that all Warriors go to the Cave and attack, and it ensures Farmers either farm or spawn new villagers, helping us scale up to kill the Dragon faster over time.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning strategy for Farmers
        # Current wheat available in the farm
        wheat_available = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat_available = int(environment.farm.wheat)

        # Number of Farmers that can be allocated to spawn Farmer: 2 per spawn, consuming 10 wheat per spawn
        k_farm = min(len(farmers) // 2, max(0, wheat_available // 10))

        spawn_farmers_list = farmers[:2 * k_farm]
        farm_candidates = farmers[2 * k_farm:]

        # Update wheat after farm spawns (approximate; environment will handle actual consumption)
        wheat_after_farm_spawns = wheat_available - 10 * k_farm

        # Number of Farmers that can be allocated to spawn Warrior: 2 per spawn, consuming 12 wheat per spawn
        k_war = min(len(farm_candidates) // 2, max(0, wheat_after_farm_spawns // 12))

        spawn_warrior_list = farm_candidates[:2 * k_war]
        remaining_farmers = farm_candidates[2 * k_war:]

        # Assign groups accordingly
        for c in spawn_farmers_list:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in spawn_warrior_list:
            environment.assign_group(c, "spawn warrior")

        # If there were no farmers, ensure we still assign any remaining warriors to cave and any farmers (none) to village
        # (Every component should be assigned exactly one group already)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village
                environment.assign_group(c, "village")
        # Note: The "cave" group can remain unused in this step; it's valid to have empty groups.
```