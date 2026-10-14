

# Adaptation Strategy for Dragon Hunt

## Strategy Description

The strategy operates in phases:

1. **Immediate deployment**: Warriors in the village are immediately sent to the cave. Once in the cave, they always attack the dragon (they never retreat, per requirements).

2. **Economy phase (farmers in village)**:
   - Farmers farm to accumulate wheat.
   - Once we have at least 2 farmers AND enough wheat (12 for warrior, 10 for farmer), we spawn new villagers.
   - Priority: Spawn warriors first (3 damage vs 1 damage is critical for killing the 50 HP dragon).
   - We track spawned counts to ensure at least 2 warriors and 2 farmers are spawned.

3. **Attack phase**: All warriors in the cave attack every step. This ensures the dragon is attacked well within the first 15 steps (warriors are sent to cave from step 0).

4. **No farmer attacks**: Farmers always stay in the village, farming or spawning. They are too weak (1 damage) and fragile (4 HP) to justify risking them.

5. **Safety**: If a farmer somehow ends up in the cave, it is sent back to the village immediately.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        wheat = environment.farm.wheat

        # All warriors in village go to cave (to eventually attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Use remaining farmers for spawning or farming
        remaining_farmers = list(farmers)

        # Priority 1: Spawn warriors (deal 3 dmg, crucial for killing dragon)
        # Need pairs of farmers and 12 wheat per warrior
        while len(remaining_farmers) >= 2 and self.spawned_warriors < 2:
            # Check actual wheat available (use observed value; be conservative)
            if environment.farm.wheat >= 12 * (self.spawned_warriors - self.spawned_warriors + 1):
                environment.assign_group(remaining_farmers[0], "spawn warrior")
                environment.assign_group(remaining_farmers[1], "spawn warrior")
                remaining_farmers = remaining_farmers[2:]
                self.spawned_warriors += 1
            else:
                break

        # Priority 2: Spawn farmers (to grow economy)
        while len(remaining_farmers) >= 2 and self.spawned_farmers < 2:
            if environment.farm.wheat >= 10:
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                self.spawned_farmers += 1
            else:
                break

        # All remaining farmers stay in village and farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon - deal 3 damage per attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in cave - send them back to village
                environment.assign_group(c, "village")
```

This strategy ensures warriors are deployed and attacking from the very first opportunity (well within 15 steps), while farmers maintain the economy and spawn additional warriors and farmers to build a force capable of dealing 50+ total damage before step 30. The warrior-focused spawning prioritizes damage output, and having 3-4 warriors attacking simultaneously should kill the dragon in roughly 6-8 attack rounds, even accounting for some losses to counter-attacks.