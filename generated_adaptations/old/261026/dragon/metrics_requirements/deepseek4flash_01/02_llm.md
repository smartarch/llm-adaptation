The strategy focuses on a balanced economy and military approach:

1. **Village management**:
   - All warriors are immediately sent to the Cave to join the attack.
   - Farmers are primarily kept in the Village. They are used either for farming (to produce wheat) or for spawning new villagers.
   - To bootstrap the economy, we prioritize spawning new farmers until we have at least 6 farmers. This ensures a steady wheat income.
   - Once we have 6 or more farmers, we switch to spawning warriors to increase the damage output against the Dragon.
   - Spawning is limited by available wheat and by the need to keep a minimum number of farmers working on the farm (at least 2 when possible). However, if we have fewer than 4 farmers, we allow using all available farmers for spawning to accelerate growth.
   - The number of spawn pairs per step is dynamically calculated based on current farmers and wheat, allowing multiple spawns in a single step if resources permit.

2. **Cave management**:
   - All warriors in the Cave are assigned to attack the Dragon continuously.
   - Any farmers that end up in the Cave are sent back to the Village to keep them safe and working on the farm.

This strategy ensures early attacks (within the first 15 steps), continuous spawning of both farmers and warriors, and keeps all warriors in the Cave attacking most of the time.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawns = 0
        self.warrior_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        
        # Send all warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        F = len(farmers)
        wheat = environment.farm.wheat
        
        # Determine how many spawn pairs we can afford without crippling farming
        if F >= 4:
            max_pairs = (F - 2) // 2
        elif F >= 2:
            max_pairs = F // 2
        else:
            max_pairs = 0
        
        num_farmer_spawns = 0
        num_warrior_spawns = 0
        wheat_left = wheat
        
        for _ in range(max_pairs):
            # Prioritize farmers until we have at least 6 farmers
            if F + num_farmer_spawns < 6 and wheat_left >= 10:
                num_farmer_spawns += 1
                wheat_left -= 10
            elif wheat_left >= 12:
                num_warrior_spawns += 1
                wheat_left -= 12
            elif wheat_left >= 10:
                num_farmer_spawns += 1
                wheat_left -= 10
            else:
                break
        
        # Assign farmers to appropriate groups
        idx = 0
        for _ in range(num_farmer_spawns):
            if idx + 1 < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                environment.assign_group(farmers[idx + 1], "spawn farmer")
                idx += 2
        for _ in range(num_warrior_spawns):
            if idx + 1 < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                environment.assign_group(farmers[idx + 1], "spawn warrior")
                idx += 2
        for i in range(idx, F):
            environment.assign_group(farmers[i], "farm")
        
        self.farmer_spawns += num_farmer_spawns
        self.warrior_spawns += num_warrior_spawns

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```