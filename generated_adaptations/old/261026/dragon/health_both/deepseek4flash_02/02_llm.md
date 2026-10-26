Based on the requirements, I'll design an adaptation strategy that balances economic growth (spawning villagers) with military pressure (attacking the Dragon). The key observations from the game mechanics are:

1. **Villagers are not consumed when spawning** – they only need to be assigned to the spawn group while wheat is consumed. This means we can repeatedly use the same farmers to spawn new villagers.
2. **Warriors deal 3 damage, farmers 1** – so we want to spawn warriors as soon as we have a stable farmer economy.
3. **Spawning requires 2 villagers per new villager** – so we should allocate farmers in pairs.
4. **Wheat is produced only by farming** – we need to balance how many farmers we put into the spawn group versus farming.

The strategy:
- **In the village**: 
  - Send all warriors to the cave.
  - For farmers, we first ensure at least 2 new farmers are spawned to grow the economy. Then we spawn as many warriors as possible (up to 2 minimum, then extra) to increase damage. We use all available wheat and farmer pairs, leaving the rest to farm.
- **In the cave**:
  - All warriors attack the Dragon.
  - Any farmers are sent back to the village to farm.

This ensures early attacks (warriors reach the cave quickly), continuous spawning of both farmers and warriors, and all warriors stay in the cave attacking.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        warriors = [c for c in components if c.role == 'Warrior']
        farmers = [c for c in components if c.role == 'Farmer']
        
        # All warriors go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        wheat = environment.farm.wheat
        num_farmers = len(farmers)
        max_pairs = num_farmers // 2
        
        # Determine how many new farmers/warriors we still need
        needed_farmers = max(0, 2 - self.spawned_farmers)
        needed_warriors = max(0, 2 - self.spawned_warriors)
        
        pairs_for_farmer = 0
        pairs_for_warrior = 0
        
        # First, try to spawn the needed farmers
        if needed_farmers > 0 and max_pairs > 0:
            affordable = wheat // 10
            take = min(needed_farmers, max_pairs, affordable)
            pairs_for_farmer = take
            wheat -= take * 10
            max_pairs -= take
        
        # Then, try to spawn the needed warriors
        if needed_warriors > 0 and max_pairs > 0:
            affordable = wheat // 12
            take = min(needed_warriors, max_pairs, affordable)
            pairs_for_warrior = take
            wheat -= take * 12
            max_pairs -= take
        
        # Any remaining capacity goes to spawning more warriors (for damage)
        if max_pairs > 0:
            affordable = wheat // 12
            take = min(max_pairs, affordable)
            pairs_for_warrior += take
            wheat -= take * 12
            max_pairs -= take
        
        # Assign farmers to spawn groups and the farm
        idx = 0
        for _ in range(2 * pairs_for_farmer):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        for _ in range(2 * pairs_for_warrior):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        for i in range(idx, num_farmers):
            environment.assign_group(farmers[i], "farm")
        
        # Update spawn counters
        self.spawned_farmers += pairs_for_farmer
        self.spawned_warriors += pairs_for_warrior

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the dragon, farmers go back to the village
        for c in components:
            if c.role == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```