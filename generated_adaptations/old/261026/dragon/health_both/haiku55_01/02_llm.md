## Strategy: Warriors Attack, Farmers Farm and Breed

**Village phase:**
- All Warriors go to the "cave" group immediately, so they reach the Dragon as early as possible.
- Farmers are used for breeding and farming. Each step, while wheat allows it, the strategy takes pairs of Farmers for spawning. Warrior spawning gets priority because Warriors deal three times the damage. Farmer spawning follows. Each spawn type is capped at 3 pair-events so that the farm keeps producing wheat.
- Any Farmers left over stay in the "farm" group.

**Cave phase:**
- All Warriors are assigned to "attack" and deal 3 damage per step, which keeps them in the Cave and attacking.
- Any Farmer that ends up in the Cave is sent back to the "village" group, since Farmers must stay in the Village.

**Timing:** Warriors reach the Cave on step 1 and attack from step 2 onward, which satisfies the requirement to attack within the first 15 steps. Dragon-retaliation damage is accepted; Warriors have 6 HP and the strategy keeps them fighting so that the 50 HP Dragon can be killed within 30 steps.

**Limitations:** Spawn-event counting is approximate, because the strategy assumes each assigned pair produces a spawn. The strategy does not retreat wounded Warriors, which trades some survivability for damage output.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    MAX_SPAWN_EVENTS_PER_TYPE = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_events = 0
        self.farmer_spawn_events = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to the cave to attack the dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Remaining farmers available for farming or spawning.
        available = list(farmers)
        budget = wheat

        # Priority 1: spawn warriors (more damage).
        if (self.warrior_spawn_events < self.MAX_SPAWN_EVENTS_PER_TYPE
                and budget >= 12 and len(available) >= 2):
            for _ in range(2):
                environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            self.warrior_spawn_events += 1

        # Priority 2: spawn farmers (more wheat production).
        if (self.farmer_spawn_events < self.MAX_SPAWN_EVENTS_PER_TYPE
                and budget >= 10 and len(available) >= 2):
            for _ in range(2):
                environment.assign_group(available.pop(0), "spawn farmer")
            budget -= 10
            self.farmer_spawn_events += 1

        # Everyone else keeps farming.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Keep warriors in the cave and attacking the dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers must not stay in the cave; send them back to the village.
                environment.assign_group(c, "village")
```