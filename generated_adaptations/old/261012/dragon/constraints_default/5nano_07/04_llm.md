Strategy reasoning and updated adaptation plan

What changed and why:
- The tests require spawning a few new warriors early to increase DPS against the Dragon. My previous approach could over-prioritize farming spawns and leave no guaranteed Warrior spawn when wheat was limited.
- Updated strategy in assign_in_village:
  - Move all Warriors to the Cave (to attack later in cave phase) as before.
  - For Farmers, adopt a Warrior-first spawning plan when possible:
    - If there are at least 2 Farmers and wheat >= 12, reserve 2 Farmers to spawn 1 Warrior (spawn warrior group). This ensures at least one Warrior is spawned as soon as possible when resources allow.
    - With the remaining Farmers, compute how many additional Warrior spawns and Farmer spawns can occur given the remaining wheat (after reserving 12 for the Warrior spawn). Each Warrior spawn requires 2 Farmers and 12 wheat; each Farmer spawn requires 2 Farmers and 10 wheat.
    - Spawn as many Farmer-spawns as possible from the leftovers, constrained by both the remaining wheat and the number of remaining Farmers (in pairs).
    - Any Farmers not allocated to spawns go to the "farm" group to keep wheat production going.
  - If wheat is insufficient for a Warrior spawn, fallback to using Farmer spawns if possible given wheat; otherwise send Farmers to farming.

This approach guarantees at least one Warrior spawn whenever the resources allow, while still enabling additional farming and possible further spawns, which increases the probability of killing the Dragon within 30 steps.

Updated Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers when they are in the Village.

        Strategy:
        - All Warriors go to the Cave (to go attack later in the cave phase).
        - Farmers: attempt to spawn Warriors first if possible (needs 2 Farmers and 12 wheat).
          Then use remaining Farmers to spawn more Farmers if wheat allows, otherwise send to farming.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to cave (to go to the Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Try to spawn at least one Warrior if possible
        initial_wheat = getattr(environment.farm, "wheat", 0)

        if len(farmers) >= 2 and initial_wheat >= 12:
            # Reserve two farmers for a Warrior spawn
            for c in farmers[:2]:
                environment.assign_group(c, "spawn warrior")
            remaining = farmers[2:]

            # Wheat left after reserving Warrior spawn
            wheat_after_warrior = initial_wheat - 12

            # 3) Spawn as many additional Farmers as possible from the remaining farmers
            # Each additional Farmer spawn requires 2 farmers and 10 wheat
            max_farmer_spawns = min(len(remaining) // 2, wheat_after_warrior // 10)
            num_to_spawn_farmers = max_farmer_spawns * 2

            for c in remaining[:num_to_spawn_farmers]:
                environment.assign_group(c, "spawn farmer")

            rest = remaining[num_to_spawn_farmers:]
            for c in rest:
                environment.assign_group(c, "farm")
        else:
            # Not enough to spawn a Warrior; fall back to Farmer spawns if possible
            if len(farmers) >= 2 and initial_wheat >= 10:
                max_pairs = min(len(farmers) // 2, initial_wheat // 10)
                num_to_spawn_farmers = max_pairs * 2
                for c in farmers[:num_to_spawn_farmers]:
                    environment.assign_group(c, "spawn farmer")
                rest = farmers[num_to_spawn_farmers:]
                for c in rest:
                    environment.assign_group(c, "farm")
            else:
                # No spawns possible; send all Farmers to farming
                for c in farmers:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers when they are in the Cave.

        Strategy:
        - Warriors go to "attack" to fight the Dragon.
        - Farmers go back to the Village to farm or spawn.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```