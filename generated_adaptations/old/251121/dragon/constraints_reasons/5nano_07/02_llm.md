Reasoning and adaptation strategy

Goal alignment:
- All Warriors should move to the Cave and then attack the Dragon as soon as they arrive.
- All Farmers should stay in the Village, farming to grow wheat and/or participating in spawning to generate more villagers.
- Spawn groups ("spawn farmer" and "spawn warrior") should be used to produce a few extra Farmers and Warriors to increase DPS against the Dragon.
- We must ensure the Dragon is attacked early (at least once within the first 15 steps) and that we have enough fighters in the Cave to deal damage.
- We should keep a substantial portion of Warriors in the Cave (attack) so they can damage the Dragon while in cave.

Strategy details:
- In assign_in_village:
  - Move all Warriors to the "cave" group so they travel to the Cave.
  - For Farmers, decide spawning vs farming based on available wheat:
    - Compute how many Warrior spawns we can support: each Warrior spawn requires 2 villagers and 12 wheat; up to floor(n_farmers/2) pairs, limited by wheat/12.
    - With remaining Farmers and wheat, compute Farmer spawns: each requires 2 villagers and 10 wheat; up to floor(remaining_farmers/2) pairs, limited by wheat/10.
    - Assign 2*k Farmers to "spawn warrior" (k = number of Warrior spawn pairs), 2*m Farmers to "spawn farmer" (m = number of Farmer spawn pairs), and the rest to "farm".
  - This ensures:
    - Some new Warriors and Farmers will be spawned (a few each when possible).
    - All Farmers remain in the Village (either farming or spawning) and all Warriors head toward the Cave.
- In assign_in_cave:
  - Move all Warriors to "attack" (they will attack the Dragon once in cave).
  - Move all Farmers back to "village" (to satisfy "All farmers should stay in the Village").
  - This guarantees:
    - All Warriors attack the Dragon after arriving in the Cave.
    - The majority of Warriors will be in the Cave (in attack) for DPS, satisfying the “at least half in the Cave most of the time” rule.

Code implementation:
- The class SmartAdaptation derives from the provided base class.
- It implements the described logic in assign_in_village and assign_in_cave.
- Spawning logic is designed to produce at least a few new villagers when resources permit, without starving the farming production.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in the village by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to cave (to travel there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers
        # Wheat available in the farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0  # If farm object isn't available for some reason

        n_farmers = len(farmers)

        # Determine how many Warrior spawns we can perform this step
        max_warrior_spawns = min(n_farmers // 2, wheat // 12)

        # Remaining farmers after allocating for Warrior spawns
        remaining_farmers = n_farmers - 2 * max_warrior_spawns

        # Determine how many Farmer spawns we can perform with remaining wheat
        max_farmer_spawns = min(remaining_farmers // 2, (wheat - 12 * max_warrior_spawns) // 10)

        # Allocate farmers to groups
        idx = 0
        # Farmers chosen for Warrior spawns
        warrior_spawn_villagers = farmers[idx: idx + 2 * max_warrior_spawns]
        idx += 2 * max_warrior_spawns

        # Farmers chosen for Farmer spawns
        farmer_spawn_villagers = farmers[idx: idx + 2 * max_farmer_spawns]
        idx += 2 * max_farmer_spawns

        # Remaining farmers will farm
        farming_farmers = farmers[idx:]

        for f in warrior_spawn_villagers:
            environment.assign_group(f, "spawn warrior")

        for f in farmer_spawn_villagers:
            environment.assign_group(f, "spawn farmer")

        for f in farming_farmers:
            environment.assign_group(f, "farm")

        # If there are any farmers not in the village after above (shouldn't happen), send them to farm by default
        # (Not strictly necessary since we assigned all farmers above)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, make all Warriors attack; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(c, "village")
```