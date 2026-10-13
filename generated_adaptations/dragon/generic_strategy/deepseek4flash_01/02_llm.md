The strategy focuses on achieving an early attack while building a sustainable economy. We prioritize spawning a warrior only if no warriors exist, ensuring an attack occurs within the first 15 steps. We then build up to 6 farmers to generate enough wheat (30 per step) to mass-produce warriors (2 per step at 12 wheat each). Once the farmer count reaches 6, we continuously spawn warriors to overwhelm the Dragon. All warriors are sent to the Cave and assigned to attack every step. Any farmers that appear in the Cave are sent back to the Village. This approach balances early pressure with long-term damage output, easily killing the Dragon within 30 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self.warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        F = len(farmers)
        W = len(warriors)
        
        # Assign all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        # Determine how many farmers to assign to spawn groups
        wheat = environment.farm.wheat
        max_spawns = F // 2
        nf = 0  # number of farmer spawns
        nw = 0  # number of warrior spawns
        remaining_spawns = max_spawns
        remaining_wheat = wheat
        projected_F = F
        
        while remaining_spawns > 0:
            # Priority 1: Spawn a warrior if we have none at all (for early attack)
            if self.warriors_spawned + nw == 0 and W == 0 and remaining_wheat >= 12:
                nw += 1
                remaining_wheat -= 12
                remaining_spawns -= 1
            # Priority 2: Ensure at least 2 farmers are spawned in total
            elif self.farmers_spawned + nf < 2 and remaining_wheat >= 10:
                nf += 1
                remaining_wheat -= 10
                remaining_spawns -= 1
                projected_F += 1
            # Priority 3: Build economy up to 6 farmers
            elif projected_F < 6 and remaining_wheat >= 10:
                nf += 1
                remaining_wheat -= 10
                remaining_spawns -= 1
                projected_F += 1
            # Priority 4: Spawn as many warriors as possible
            elif remaining_wheat >= 12:
                nw += 1
                remaining_wheat -= 12
                remaining_spawns -= 1
            else:
                break
        
        # Update cumulative spawn counts
        self.farmers_spawned += nf
        self.warriors_spawned += nw
        
        # Assign farmers to groups
        spawn_farmer_count = nf * 2
        spawn_warrior_count = nw * 2
        assigned_farmer = 0
        assigned_warrior = 0
        for f in farmers:
            if assigned_farmer < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
                assigned_farmer += 1
            elif assigned_warrior < spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
                assigned_warrior += 1
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                environment.assign_group(c, "village")
```