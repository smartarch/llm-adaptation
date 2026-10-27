

## Strategy Description

My adaptation strategy follows these principles:

1. **Meal Management**: Priority is given to villagers who must eat (steps_since_meal >= 5). Warriors eat before going to cave if steps_since_meal >= 3. Warriors in cave leave for village when steps_since_meal >= 4 (so they arrive at village with steps_since_meal = 5 and can eat the next step).

2. **Attack Rotation**: Warriors attack the dragon for up to 3 steps per cycle (steps_since_meal 1→2→3→4, then leave). With 3+ warriors staggered, the dragon is attacked every step. If all warriors would leave simultaneously, one stays to attack (maintaining the max 2 unattacked steps constraint).

3. **Spawning**: Early game prioritizes warrior spawning (2 farmers → 1 warrior for 12 wheat) to build attacking force. After step 5, also spawns farmers (2 farmers → 1 farmer for 10 wheat) to boost wheat production. Spawning continues through step 20.

4. **Farmers**: Stay in village to farm, spawn new villagers, or eat. Never sent to cave.

5. **Dragon Attack Timing**: Warriors are sent to cave as soon as they're not too hungry (steps_since_meal < 3), ensuring first attack within 15 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_attack = False

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Priority 1: MUST EAT (steps_since_meal >= 5)
        must_eat_ids = set()
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                must_eat_ids.add(id(c))

        # Remaining warriors (not forced to eat)
        remaining_warriors = [c for c in warriors if id(c) not in must_eat_ids]

        # Warriors: eat if getting hungry, otherwise go to cave
        warriors_eat = []
        warriors_cave = []
        for c in remaining_warriors:
            if c.steps_since_meal >= 3:
                warriors_eat.append(c)
            else:
                warriors_cave.append(c)

        for c in warriors_eat:
            environment.assign_group(c, "eat")
        for c in warriors_cave:
            environment.assign_group(c, "cave")

        # Farmers: eat, spawn, or farm
        remaining_farmers = [c for c in farmers if id(c) not in must_eat_ids]

        # Farmers that should eat soon (plan ahead to avoid emergencies)
        farmers_eat = [c for c in remaining_farmers if c.steps_since_meal >= 3]
        farmers_other = [c for c in remaining_farmers if c.steps_since_meal < 3]

        for c in farmers_eat:
            environment.assign_group(c, "eat")

        # Spawning logic
        # Priority: spawn warriors early for attack power, then balance with farmers
        spawn_pool = list(farmers_other)

        if step <= 8 and len(spawn_pool) >= 2 and wheat >= 12:
            # Early game: spawn warriors aggressively
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            spawn_pool = spawn_pool[2:]
            # Try to spawn a second pair if we have enough
            if len(spawn_pool) >= 2 and wheat >= 24:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
                spawn_pool = spawn_pool[2:]

        elif step <= 20 and len(spawn_pool) >= 2 and wheat >= 12:
            # Mid game: keep spawning warriors
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            spawn_pool = spawn_pool[2:]

        elif step >= 5 and len(spawn_pool) >= 2 and wheat >= 10:
            # Spawn a farmer for more wheat production
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            spawn_pool = spawn_pool[2:]
            # Also try to spawn a warrior if we have resources
            if len(spawn_pool) >= 2 and wheat >= 22:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
                spawn_pool = spawn_pool[2:]

        # All remaining farmers: farm
        for c in spawn_pool:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers in cave (shouldn't happen but handle it): return to village
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors: attack or go to village to eat
        must_leave = [c for c in warriors if c.steps_since_meal >= 4]
        can_stay = [c for c in warriors if c.steps_since_meal < 4]

        # Safety: if no warrior can stay and at least one must leave,
        # keep the one with the lowest steps_since_meal to attack
        # (they'll be at 5 next step and go to village then)
        # This ensures dragon is not left unattacked for >2 steps
        if not can_stay and must_leave:
            must_leave.sort(key=lambda c: c.steps_since_meal)
            keeper = must_leave.pop(0)
            environment.assign_group(keeper, "attack")

        for c in can_stay:
            environment.assign_group(c, "attack")

        for c in must_leave:
            environment.assign_group(c, "village")
```