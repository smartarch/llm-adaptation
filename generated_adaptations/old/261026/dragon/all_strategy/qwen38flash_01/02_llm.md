

## Strategy Description

My adaptation strategy follows these principles:

1. **Warriors always go to the cave and attack** - They deal 3 damage/step and have 6 HP, making them the primary damage dealers. They never return to the village.

2. **Farmers stay in the village** - They farm (5 wheat/step) or spawn new villagers. The spawning priority is:
   - **First 2 steps**: Spawn warriors (1 per step, using 2 farmers each, costing 12 wheat) - to build attack power early
   - **Next 2 steps**: Spawn farmers (1 per step, using 2 farmers each, costing 10 wheat) - to sustain wheat production
   - **After that**: All farmers just farm

3. **Early attack requirement**: Warriors go to cave immediately (step 0), satisfying the "attack within first 15 steps" requirement.

4. **In the cave**: All warriors attack unconditionally (as specified). Any farmer mistakenly in the cave gets sent back to the village.

5. **Stopping condition**: Once 2 warriors and 2 farmers have been spawned, no more spawning occurs to maximize farming output.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors immediately head to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic: want at least 2 warriors and 2 farmers spawned
        # Each spawn of 1 villager requires 2 villagers in the spawn group + wheat cost
        farmer_idx = 0

        # Priority 1: Spawn warriors (for damage output) - up to 1 per step
        if self.spawned_warriors < 2 and farmer_idx + 2 <= len(farmers) and wheat >= 12:
            environment.assign_group(farmers[farmer_idx], "spawn warrior")
            environment.assign_group(farmers[farmer_idx + 1], "spawn warrior")
            farmer_idx += 2
            wheat -= 12
            self.spawned_warriors += 1

        # Priority 2: Spawn farmers (for wheat sustainability) - up to 1 per step
        elif self.spawned_farmers < 2 and farmer_idx + 2 <= len(farmers) and wheat >= 10:
            environment.assign_group(farmers[farmer_idx], "spawn farmer")
            environment.assign_group(farmers[farmer_idx + 1], "spawn farmer")
            farmer_idx += 2
            wheat -= 10
            self.spawned_farmers += 1

        # All remaining farmers work on the farm
        for i in range(farmer_idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon from the cave
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in the cave; send them back to village
                environment.assign_group(c, "village")
```