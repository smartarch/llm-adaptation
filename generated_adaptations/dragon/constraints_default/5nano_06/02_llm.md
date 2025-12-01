Reasoning and adaptation strategy

Goal and constraints
- All Warriors should go to the Cave and attack the Dragon.
- All Farmers should stay in the Village and either farm to produce Wheat or participate in spawning to grow the population (both Farmers and Warriors may be needed later).
- Spawning rules: 
  - spawn farmer: for every two villagers assigned to the "spawn farmer" group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to the "spawn warrior" group and 12 wheat, a new Warrior is spawned.
- We need to assign each component (villager) to exactly one group in each step.
- We can observe environment.farm.wheat and environment.dragon.hp, but we cannot directly modify those values; spawning is driven by group assignments and available wheat.
- The dragon has a starting HP of 50 and the game has a 30-step hard limit.

Strategy overview
- Core principle: maximize DPS while ensuring sustainability. This means:
  - Always move Warriors to the Cave to attack the Dragon (attack group in cave context).
  - Keep Farmers in the Village for farming by default, to accumulate Wheat for spawning and to produce more villagers over time.
  - Use spawn groups to grow the population when Wheat is sufficient. We allocate Farmers to two possible spawn groups (spawn farmer and spawn warrior) to generate new Villagers as Wheat allows. The allocation is constrained by:
    - The number of Farmers available in the Village.
    - The available Wheat (environment.farm.wheat).
    - The need to form pairs (two villagers in the spawn group) to trigger spawns.
  - Spawn planning within a single step (in assign_in_village):
    - Compute how many Farmer spawns can be supported: max_fspawn_pairs = min(total_farmers // 2, wheat // 10).
    - After reserving Farmers for Farmer spawns, compute how many Warrior spawns can be supported with remaining Wheat: max_wspawn_pairs = min( remaining_farmers_after_farm // 2, remaining_wheat // 12 ).
    - Assign the corresponding numbers of Farmers to the two spawn groups to trigger spawns; the actual spawning will occur based on the engine’s mechanics when those groups exist and Wheat is available.
  - In the Cave step (assign_in_cave):
    - All Warriors go to the "attack" group to strike the Dragon.
    - All Farmers move back to the Village via the "village" group (to keep farming or spawn more villagers).

Implementation notes
- We implement a deterministic, step-stable rule: Warriors in Village go to Cave; Farmers in Village are split into three groups based on Wheat availability and the spawn planning described above.
- In Cave, Farmers are moved to the Village; Warriors go to Attack.
- The solution uses only the provided environment.assign_group API calls.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers currently in the Village into categories based on their role.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Move all Warriors to the Cave (attack later in assign_in_cave context)
        for w in warriors:
            environment.assign_group(w, "cave")  # send to cave to eventually attack

        # Step 2: Handle Farmers in the Village
        # We want Farmers to farm by default, but we may allocate some to spawn groups
        total_farmers = len(farmers)

        if total_farmers == 0:
            return  # nothing else to assign

        # Current wheat available for spawning (note: we compute with a simple heuristic)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # First, determine how many Farmer spawns can be supported by wheat
        # Need 10 wheat per 2 farmers (i.e., per 1 pair)
        max_fspawn_pairs = min(total_farmers // 2, wheat // 10)

        # Reserve farmers for Farmer spawns
        spawn_farm_count = 2 * max_fspawn_pairs
        farmers_for_farm = total_farmers - spawn_farm_count  # rest can be used for farming or Warrior spawns

        remaining_wheat_after_farm_spawns = max(0, wheat - max_fspawn_pairs * 10)

        # Now determine how many Warrior spawns can be supported with remaining wheat
        remaining_farmers_after_farm_spawns = farmers_for_farm
        max_wspawn_pairs = min(remaining_farmers_after_farm_spawns // 2, remaining_wheat_after_farm_spawns // 12)

        spawn_warrior_count = 2 * max_wspawn_pairs
        farmers_for_warrior_spawns = spawn_warrior_count

        # Remaining farmers go to farming in Village
        farmers_for_regular_farm = total_farmers - (spawn_farm_count + farmers_for_warrior_spawns)

        # Now assign groups accordingly
        # First, assign spawn farmer farmers
        index = 0
        for i in range(spawn_farm_count):
            if index < len(farmers):
                environment.assign_group(farmers[index], "spawn farmer")
                index += 1

        # Next, assign spawn warrior farmers (if any)
        for i in range(farmers_for_warrior_spawns):
            if index < len(farmers):
                environment.assign_group(farmers[index], "spawn warrior")
                index += 1

        # Remaining farmers go to normal farming
        for i in range(farmers_for_regular_farm):
            if index < len(farmers):
                environment.assign_group(farmers[index], "farm")
                index += 1

        # In case there were any farmers left unassigned due to edge cases, default assign to farm
        while index < len(farmers):
            environment.assign_group(farmers[index], "farm")
            index += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Divide Cave villagers:
        # - Warriors should attack -> group "attack"
        # - Farmers should go back to Village -> group "village"
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any other roles) go to Village
                environment.assign_group(c, "village")
```