Reasoning and updated adaptation strategy:
- Goal remains to kill the Dragon quickly while respecting constraints: all Warriors must go to the Cave to attack, all Farmers stay in the Village to farm and to enable spawning.
- Key improvement ideas:
  - Spawn decisions should be dynamic and data-driven. Only spawn as many new Farmers as allowed by both the number of available Farmers (in pairs) and the wheat currently available in the Farm.
  - If there is enough wheat to spawn, allocate 2 * spawn_count Farmers to the "spawn farmer" group, where spawn_count is min(floor(num_farmers/2), floor(wheat/10)).
  - If there isn’t enough wheat to spawn, keep Farmers farming in the "farm" group to maximize wheat production for future turns.
  - In the Cave, keep Warriors in "attack" and move Farmers back to "village" to continue farming/spawning there.
- This approach aims to maximize near-term DPS by keeping Warriors attacking, while ensuring Wheat production and population growth are optimized for subsequent turns.

Python code (class implementation):

```py
import abc

# Assuming the base class can be imported from the given module path
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to "cave" (attack)
        # - Farmers stay in Village; decide between "farm" and "spawn farmer"
        #   Spawn count = min(floor(num_farmers/2), floor(wheat/10))
        #   Assign 2 * spawn_count farmers to "spawn farmer" group; rest to "farm"

        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all warriors to cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Number of farmers available to participate in spawning
        num_farmers = len(farmers)

        # Compute spawn capacity
        max_spawns_by_wheat = wheat // 10
        max_spawns_by_villagers = num_farmers // 2

        spawn_count = min(max_spawns_by_wheat, max_spawns_by_villagers)

        # Assign 2*spawn_count farmers to "spawn farmer"
        spawn_farmer_candidates = farmers[: 2 * spawn_count]
        remaining_farmers = farmers[2 * spawn_count:]

        for f in spawn_farmer_candidates:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers stay in farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy:
        # - All Warriors in the Cave go to "attack"
        # - All Farmers in the Cave go to "village" (to return to Village)

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: assign unknowns to cave by default to be safe
                environment.assign_group(c, "cave")
```