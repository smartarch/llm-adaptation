Reasoning and improved strategy

What went wrong previously:
- The spawning logic was deterministic but may not adapt well to the available wheat and the changing farm output. If wheat is scarce early, spawning too aggressively can stall growth; if wheat is abundant, delaying spawns wastes potential population growth.
- The strategy also didn’t aggressively adapt to the dragon’s hp and remaining steps. We should push for early population growth to maximize both wheat production and firing power, while keeping warriors consistently contributing by attacking the dragon.

Improved adaptation strategy:
- In the village, organize spawning in two deterministic phases, but driven purely by current resource availability and the number of farmers:
  - Phase 1: Use as many Farmer spawns as possible (two farmers + 10 wheat) from the available pool. This boosts population with farmers who will later farm or spawn more villagers.
  - Phase 2: Use remaining farmers to spawn Warriors (two farmers + 12 wheat) if wheat permits. This increases offensive capability without waiting for future turns.
  - Phase 3: Any remaining farmers stay in farming to produce more wheat for future turns.
- Warriors always go to the Cave to attack the Dragon.
- In the cave, Farmers go back to the Village, staying true to the requirement that Farmers stay in Village to farm or spawn.
- Step-awareness: the two-phase spawn uses the current wheat and number of farmers, so the plan adapts to early or late-game wheat stock and population.

This approach aims to:
- Grow the population quickly when wheat allows, increasing future wheat production and the damage potential over successive steps.
- Ensure Warriors consistently contribute damage by attacking the Dragon as soon as they reach the Cave.
- Keep Farmers in the Village for farming/spawning, maximizing wheat production for subsequent steps.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning (best effort to read current wheat)
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            try:
                wheat = int(environment.farm.wheat)
            except Exception:
                wheat = 0

        n_farmers = len(farmers)
        assigned_to_spawn_farm = 0
        assigned_to_spawn_warrior = 0

        i = 0
        # Phase 1: Spawn as many farmers as possible (2 farmers + 10 wheat)
        while i + 1 < n_farmers and wheat >= 10:
            c1 = farmers[i]
            c2 = farmers[i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            assigned_to_spawn_farm += 2
            i += 2
            wheat -= 10

        # Phase 2: With remaining farmers, spawn warriors (2 farmers + 12 wheat)
        while i + 1 < n_farmers and wheat >= 12:
            c1 = farmers[i]
            c2 = farmers[i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            assigned_to_spawn_warrior += 2
            i += 2
            wheat -= 12

        # Phase 3: Remaining farmers stay in farming
        for idx in range(n_farmers):
            c = farmers[idx]
            if idx < i:  # already assigned to a spawn group
                continue
            environment.assign_group(c, "farm")

        # All Warriors go to the Cave (to attack Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```