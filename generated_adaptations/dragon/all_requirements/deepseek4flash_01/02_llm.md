The strategy focuses on maintaining a balance between economy (farmers) and damage (warriors) while adhering to the functional requirements.

**Village assignment:**
- All warriors are immediately sent to the Cave (`"cave"`).
- Farmers are primarily kept in the Village. We use a subset of farmers to spawn new villagers.
- Early on (first 10 steps), we alternate between spawning warriors (even steps) and farmers (odd steps) when enough wheat is available. This ensures both new warriors and new farmers are created quickly.
- After the early game, we aim to maintain a healthy farmer count (around 6). If we have fewer than 6 farmers, we prioritize spawning a farmer; otherwise, we spawn a warrior.
- If the Dragon's HP drops below 20, we prioritize spawning warriors to finish it off.
- For spawning, we assign exactly two farmers to the chosen spawn group (meeting the minimum requirement) and assign the remaining farmers to work on the farm.

**Cave assignment:**
- All warriors are assigned to `"attack"` the Dragon.
- Any farmers that find themselves in the Cave are sent back to the Village (`"village"`), ensuring they stay in the Village as required.

This approach guarantees that all warriors attack, farmers remain in the Village, and both new farmers and warriors are spawned multiple times, while ensuring the Dragon is attacked early.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        
        # All warriors immediately go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")
        
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        
        spawn_warrior = False
        spawn_farmer = False
        
        if len(farmers) >= 2:
            if step < 10:
                # Early game: alternate to get both types quickly
                if step % 2 == 0:  # even steps: prioritize warrior
                    if wheat >= 12:
                        spawn_warrior = True
                    elif wheat >= 10:
                        spawn_farmer = True
                else:  # odd steps: prioritize farmer
                    if wheat >= 10:
                        spawn_farmer = True
                    elif wheat >= 12:
                        spawn_warrior = True
            elif dragon_hp < 20:
                # Dragon is weak: prioritize warriors to finish it
                if wheat >= 12:
                    spawn_warrior = True
                elif wheat >= 10:
                    spawn_farmer = True
            else:
                # Maintain a healthy farmer count, then spawn warriors
                if len(farmers) < 6 and wheat >= 10:
                    spawn_farmer = True
                elif wheat >= 12:
                    spawn_warrior = True
                elif wheat >= 10:
                    spawn_farmer = True
        
        # Assign farmers to spawn groups (at most 2 per step, using first two available)
        assigned_spawn = 0
        if spawn_warrior:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn warrior")
            assigned_spawn = 2
        elif spawn_farmer:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn farmer")
            assigned_spawn = 2
        
        # Remaining farmers work on the farm
        for f in farmers[assigned_spawn:]:
            environment.assign_group(f, "farm")
    
    def assign_in_cave(self, components, environment, group_ids, step: int):
        # All warriors attack the Dragon; farmers return to the Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```