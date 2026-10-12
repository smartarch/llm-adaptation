Reasoning and adaptation strategy

Task understanding:
- You control villagers; there are Farmers and Warriors.
- Farmers stay in the Village and can farm (produce wheat) or be allocated to spawn groups to create more villagers. Warriors head to the Cave to help attack the Dragon.
- Spawning rules: "spawn farmer" and "spawn warrior" trigger new Farmers/Warriors when at least two villagers are assigned to the group and there is enough wheat (10 wheat for a Farmer spawn, 12 wheat for a Warrior spawn). Each spawn consumes the required wheat.
- The Dragon can retaliate each time it is attacked, and if villagers die, you lose. You win if Dragon HP reaches 0 within 30 steps.

Strategy overview:
- Primary objective is to maximize damage to the Dragon as fast as possible while maintaining village wheat production. This means:
  - Move all Warriors to the Cave to attack the Dragon as soon as possible.
  - Keep Farmers in the Village to farm and generate wheat; use spawning to grow the population for stronger future attacks.
  - Spawn planning should be aggressive when wheat is available, but not so aggressive that wheat is exhausted too early (which would stall farming and future spawns).
- Spawn logic (in assign_in_village):
  - If wheat >= 22 and there are at least 4 Farmers, spawn 2 Farmers (spawn farmer) and 2 Warriors (spawn warrior) by assigning 2 farmers to each respective spawn group. This yields up to 2 new Villagers in one step, and leverages the wheat efficiently.
  - Else if wheat >= 12 and there are at least 2 Farmers, spawn 1 Warrior (spawn warrior) by assigning 2 Farmers to the spawn warrior group.
  - Else if wheat >= 10 and there are at least 2 Farmers, spawn 1 Farmer (spawn farmer) by assigning 2 Farmers to the spawn farmer group.
  - In all other cases, assign all Farmers to the regular farming group (farm).
  - Warriors in the village should be assigned to the cave (they will travel to the Cave).
- assign_in_cave logic:
  - All Warriors in the Cave should attack the Dragon (group "attack").
  - All Farmers in the Cave should go to the Village (group "village"), since Farmers should stay in the Village to farm or spawn new villagers.

Why this approach:
- It guarantees Warriors contribute to the Dragon's HP reduction as soon as possible.
- It maintains wheat production by default (Farmers are assigned to farming unless used for spawning) to enable future spawns.
- It uses spawning opportunistically when wheat allows, balancing short-term damage with long-term population growth to sustain high DPS within the 30-step limit.

Code implementation (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in village into groups:
        # - Warriors -> cave (to go to Cave and attack later)
        # - Farmers -> farm / spawn groups (spawn decisions depend on wheat)

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Spawn planning based on wheat and number of farmers available
        wheat = getattr(environment.farm, "wheat", 0)

        # We'll prepare a map from member -> target group
        target_group = {}

        # First, assign all Warriors in village to go to cave (to be attacked later in assign_in_cave)
        for w in warriors:
            target_group[w] = "cave"

        # Now plan spawn allocations for Farmers
        # Helper: we need to allocate at least 2 farmers to a spawn group to trigger a spawn.
        # We'll try the most aggressive plan first if possible.
        if wheat >= 22 and len(farmers) >= 4:
            # Spawn 2 farmers (spawn farmer) and 2 warriors (spawn warrior)
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn farmer"
            for i, f in enumerate(farmers[2:4]):
                target_group[f] = "spawn warrior"
            # Remaining farmers (if any) go to farm
            for f in farmers[4:]:
                target_group[f] = "farm"
        elif wheat >= 12 and len(farmers) >= 2:
            # Spawn 1 Warrior (spawn warrior) using 2 farmers
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn warrior"
            # Remaining farmers (if any) go to farm
            for f in farmers[2:]:
                target_group[f] = "farm"
        elif wheat >= 10 and len(farmers) >= 2:
            # Spawn 1 Farmer (spawn farmer) using 2 farmers
            for i, f in enumerate(farmers[:2]):
                target_group[f] = "spawn farmer"
            # Remaining farmers (if any) go to farm
            for f in farmers[2:]:
                target_group[f] = "farm"
        else:
            # No spawning this step; all farmers stay and farm
            for f in farmers:
                target_group[f] = "farm"

        # If there were farmers not mentioned (shouldn't happen), assign to farm
        for f in farmers:
            if f not in target_group:
                target_group[f] = "farm"

        # Now apply assignments
        for comp, gid in target_group.items():
            environment.assign_group(comp, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In cave, make Warriors attack and move Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Farmers should go to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role
                environment.assign_group(c, "cave")
```