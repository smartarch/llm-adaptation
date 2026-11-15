

Looking at this problem, I need to design a strategy that:
1. Sends warriors to attack the dragon continuously
2. Keeps farmers in the village producing wheat and spawning new villagers
3. Ensures all villagers eat every 6 steps
4. Prevents the dragon from regenerating (attack every ≤2 steps)
5. Spawns at least 2 additional warriors and 2 farmers

**Key insights:**
- Warriors cycle: Village → Cave (1 step travel) → Attack ×3 → Village (1 step travel) → Eat → repeat (~6 step cycle)
- Staggering 2+ warriors ensures the dragon is always attacked
- Warriors must leave cave at `steps_since_meal >= 4` to arrive at village with sme=5 and eat before starving
- Warriors in village eat at sme >= 4 before going to cave (don't send them hungry)
- Farmers spawn warriors first (more damage), then farmers (more wheat), then farm

```py
import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        # Categorize villagers
        must_eat = []       # sme >= 5: critical, will starve next step
        warriors_eat = []   # sme == 4: should eat before going to cave
        warriors_go = []    # sme < 4: ready to go to cave
        farmers_pool = []   # farmers available for tasks (sme < 5)
        farmers_eat = []    # farmers that need to eat (handled by must_eat)

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    must_eat.append(c)
                elif c.steps_since_meal >= 4:
                    warriors_eat.append(c)
                else:
                    warriors_go.append(c)
            else:  # Farmer
                if c.steps_since_meal >= 5:
                    must_eat.append(c)
                else:
                    farmers_pool.append(c)

        # Priority 1: Anyone with sme >= 5 MUST eat
        for c in must_eat:
            environment.assign_group(c, "eat")

        # Priority 2: Warriors at sme 4 should eat before going to cave
        for c in warriors_eat:
            environment.assign_group(c, "eat")

        # Priority 3: Ready warriors go to cave to attack
        for c in warriors_go:
            environment.assign_group(c, "cave")

        # Handle farmers: spawning and farming
        # Try to spawn warriors first (need 2 villagers + 12 wheat), up to 3
        # Then spawn farmers (need 2 villagers + 10 wheat), up to 2
        # Then remaining farmers go to farm

        available = list(farmers_pool)

        # Spawn warriors (cost 12 wheat per spawn, need 2 villagers)
        while len(available) >= 2 and wheat >= 12 and self.spawned_warriors < 3:
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers (cost 10 wheat per spawn, need 2 villagers), up to 2
        while len(available) >= 2 and wheat >= 10 and self.spawned_farmers < 2:
            environment.assign_group(available.pop(0), "spawn farmer")
            environment.assign_group(available.pop(0), "spawn farmer")
            wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers farm
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Warriors in cave: attack if not hungry, return to village to eat
        # Non-warriors (farmers shouldn't be here, but handle anyway): go to village
        # Also handle the dragon regeneration constraint:
        # Don't leave dragon unattacked >2 steps. If a warrior at sme=4 is the
        # only one, let them attack once more (sme=5) and go next step.

        warriors = [c for c in components if c.role == "Warrior"]
        non_warriors = [c for c in components if c.role != "Warrior"]

        # Count warriors that can still attack (sme < 4)
        attackers_available = sum(1 for w in warriors if w.steps_since_meal < 4)

        for c in warriors:
            if c.steps_since_meal >= 5:
                # Critical: must leave now even though will lose HP
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= 4:
                # Should return to village to eat (arrive sme=5, eat next step)
                # But if no other warrior can attack and dragon regen is a risk,
                # still send them back - better to have 2-step gaps with regen
                # than to starve a warrior
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")

        # Non-warriors (e.g. farmers accidentally in cave) go back to village
        for c in non_warriors:
            environment.assign_group(c, "village")
```