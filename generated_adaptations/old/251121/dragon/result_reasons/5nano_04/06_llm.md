Reasoning and updated strategy

Goal recap and what to improve:
- We want a faster, more reliable kill of the Dragon, ideally within fewer steps.
- Key levers: moving Warriors to the Cave early, spawning new villagers to increase DPS and wheat production, and keeping Farmers in the Village to sustain wheat.
- The previous approach spawned at most one pair per step and didn’t aggressively leverage wheat to grow both Farmers and Warriors as soon as possible.

What I’m changing:
- Aggressive, per-step spawning plan that can trigger multiple spawns in a single step as long as wheat allows and enough Farmers exist to act as spawners.
- Spawn logic is explicit and parallel:
  - Spawn Farmer pairs as long as there are at least 2 Farmers and at least 10 wheat.
  - After Farmer spawns, spawn Warrior pairs if there are at least 2 additional Farmers available and at least 12 wheat.
- Warriors are always sent to the Cave to attack, and Farmers stay in the Village (or return to Village in the Cave phase). This keeps a steady pipeline of DPS and wheat production.
- In the Cave phase, all Warriors attack and Farmers go back to the Village.

This approach aims to:
- Ensure the Dragon is attacked early (within the first 15 steps) by having Warriors reach the Cave quickly.
- Increase population of both Farmers and Warriors rapidly when wheat is available.
- Maintain enough Warriors in the Cave to sustain DPS while Wheat production remains strong due to Farmers in the Village.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the Cave to head to the Dragon.
        # - Keep Farmers in the Village by default (farm group) to maximize wheat production.
        # - Aggressively spawn new Farmers and Warriors when wheat allows.
        #   - Spawn Farmer pairs for every 2 farmers and 10 wheat.
        #   - Then spawn Warrior pairs for every 2 farmers (after farmers were allocated to farming/spawn) and 12 wheat.
        if not components:
            return

        # Classify villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the cave to head to the Dragon
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Keep Farmers in the Village (default farming)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Spawn farmers and warriors based on available wheat
        wheat = getattr(environment.farm, "wheat", 0)

        # Number of farmer spawns we can trigger this step
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Trigger farmer spawns
        for i in range(n_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # After allocating farmer spawns, determine remaining farmers for warrior spawns
        idx_after_farm_spawns = 2 * n_farm_spawns
        remaining_farmers = len(farmers) - idx_after_farm_spawns

        # Number of warrior spawns we can trigger this step
        n_war_spawns = min(remaining_farmers // 2, wheat // 12)

        # Trigger warrior spawns
        for i in range(n_war_spawns):
            c1 = farmers[idx_after_farm_spawns + 2 * i]
            c2 = farmers[idx_after_farm_spawns + 2 * i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```