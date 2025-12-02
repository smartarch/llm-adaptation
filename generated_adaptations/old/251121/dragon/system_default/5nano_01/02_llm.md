Reasoning and adaptation strategy:
- Goal alignment: Warriors should always head to the Cave to attack the Dragon, while Farmers stay in the Village to farm or spawn new villagers. This shapes the two-phase assignment logic: in the Village, move Warriors to the Cave via the "cave" group; use Farmers to farm and to spawn new Farmers/Warriors via the dedicated spawn groups. In the Cave, move Warriors to the "attack" group to attack the Dragon, and move Farmers back to the Village via the "village" group.
- Spawn logic: Spawns are controlled by the combination of two villagers assigned to a spawn group and a wheat threshold. We compute how many spawns we can trigger this step given current wheat:
  - For spawns of Farmers: each spawn requires 2 villagers (assigned to "spawn farmer") and 10 wheat. We can trigger max_farm_spawns = min(number_of_farmers // 2, wheat // 10).
  - For spawns of Warriors: after reserving wheat for Farmer spawns, we can trigger max_warrior_spawns = min((remaining_farmers) // 2, remaining_wheat // 12).
- Allocation plan in village:
  - Move all Warriors to the "cave" group (to go to the Cave).
  - Use as many Farmers as possible to spawn new Farmers via "spawn farmer" (2 Farmers per spawn, consuming 10 wheat per spawn).
  - Use remaining Farmers to spawn Warriors via "spawn warrior" (2 Farmers per spawn, consuming 12 wheat per spawn).
  - All remaining Farmers go to the "farm" group to produce more wheat.
  - This keeps initial Military force in the Cave while expanding population and wheat production in the Village.
- Allocation plan in cave:
  - Warriors go to the "attack" group to fight the Dragon.
  - Farmers stay in the Village by sending them to the "village" group.

Python code (class SmartAdaptation) implementing the strategy:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute how many spawns we can trigger this step
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        remaining_wheat_after_farm = max(0, wheat - max_farm_spawns * 10)

        remaining_farmers_after_farm_spawns = len(farmers) - (max_farm_spawns * 2)

        max_warrior_spawns = min(remaining_farmers_after_farm_spawns // 2,
                                 remaining_wheat_after_farm // 12)

        # Assign groups for Farmers
        # First, 2*max_farm_spawns Farmers to "spawn farmer"
        farm_spawn_farmers = farmers[:2 * max_farm_spawns]
        # Next, 2*max_warrior_spawns Farmers to "spawn warrior"
        warrior_spawn_start = 2 * max_farm_spawns
        farm_spawn_warriors = farmers[warrior_spawn_start: warrior_spawn_start + 2 * max_warrior_spawns]
        # Remaining farmers go to farming
        farm_farmers = farmers[warrior_spawn_start + 2 * max_warrior_spawns:]

        # Assign groups for Farmers
        for c in farm_spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        for c in farm_spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        for c in farm_farmers:
            environment.assign_group(c, "farm")

        # Assign all Warriors to the cave (to go attack later)
        for c in warriors:
            environment.assign_group(c, "cave")

        # If there are any remaining villagers (edge case), ensure they go somewhere sensible
        # For safety, send any remaining farmers (if any were not listed above) to farming
        # (Not strictly necessary due to slicing above, but harmless)
        assigned = set(farm_spawn_farmers) | set(farm_spawn_warriors) | set(farm_farmers) | set(warriors)
        for c in components:
            if c not in assigned and getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "farm")

        # Note: Farmers going to "cave" is not desired; Warriors are the only ones that should head to the cave.
        # The "spawn" groups inherently keep a portion of Farmers growing the village.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```