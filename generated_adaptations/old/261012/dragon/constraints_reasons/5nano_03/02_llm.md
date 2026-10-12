Strategy reasoning (descriptive plan)

- Core objective alignment
  - All Warriors should eventually assault the Dragon by going to the Cave and then to the Attack group there.
  - All Farmers should remain in the Village, but they can help the population grow by spawning new villagers.
  - Spawning mechanics: For every two villagers assigned to a spawn group and the required wheat, one new villager is spawned (a Farmer for the “spawn farmer” group, and a Warrior for the “spawn warrior” group). Wheat costs are 10 for a Farmer spawn and 12 for a Warrior spawn.
  - We must ensure:
    - The Dragon is attacked at least once within the first 15 steps.
    - At least a few new farmers and a few new warriors are spawned to raise the DPS.
    - All warriors go to the Cave and then attack the Dragon.
    - At least half of the warriors should be in the Cave most of the time so they can attack.
- Practical adaptation design
  - In assign_in_village:
    - Move all existing Warriors to the cave by assigning them to the "cave" group (they will travel to the Cave).
    - Keep Farmers in Village (default to "farm" group), but also opportunistically create spawn opportunities:
      - Use as many Farmers as possible to form the "spawn farmer" group, limited by 2 farmers per spawn and 10 wheat per spawn.
      - After allocating to spawn farmers, use any remaining Farmers to form the "spawn warrior" group, limited by 2 villagers per spawn and 12 wheat per spawn, subject to the remaining wheat.
      - The rest of Farmers stay in Village ("farm" group).
    - This preserves the rule that Farmers stay in Village and enables spawning to quickly increase both Farmer and Warrior counts.
  - In assign_in_cave:
    - All Warriors currently in the Cave should be moved to the "attack" group so they attack the Dragon as soon as they are in the Cave.
    - Farmers in the Cave (if any) should be returned to the Village by assigning them to the "village" group, maintaining "Farmers stay in Village" as a policy.
  - Step constraints:
    - Since we ensure Warriors are moved to Cave in assign_in_village and then to Attack in assign_in_cave, the Dragon will be attacked early (within the first step when possible, and certainly by the first 15 steps if there are Warriors).
    - We explicitly re-assign groups for every component to satisfy the requirement that components re-assign to their new group each step.
- Assumptions and notes
  - The environment handles the actual spawning when the two required villagers are assigned to a spawn group and the wheat threshold is met; our strategy ensures those conditions by distributing farmers into spawn groups based on wheat.
  - We treat the “spawn” groups as in-village actions; spawned villagers join the Village and can later be assigned to Cave to attack.

Python code (SmartAdaptation class)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Strategy:
        # - Move all existing Warriors to the Cave (to go attack)
        # - Farmers stay in Village, but some may be allocated to spawn groups
        #   to spawn new Farmers/Warriors depending on wheat availability.

        # Move all Warriors to the Cave (they will travel to the Cave)
        for w in warriors:
            environment.assign_group(w, 'cave')

        # Spawn planning using Farmers in the Village
        available_wheat = getattr(environment.farm, 'wheat', 0)

        # Number of spawns for Farmers (2 farmers per spawn, cost 10 wheat)
        spawn_farmers = min(len(farmers) // 2, available_wheat // 10)

        # Assign 2*spawn_farmers farmers to the "spawn farmer" group
        to_spawn_farmers = farmers[:spawn_farmers * 2]
        for f in to_spawn_farmers:
            environment.assign_group(f, 'spawn farmer')

        # Remaining farmers after farming spawns
        remaining_farmers = farmers[spawn_farmers * 2:]

        # Wheat left after farmer spawns
        wheat_after_farm_spawns = max(0, available_wheat - spawn_farmers * 10)

        # Number of spawns for Warriors (2 villagers per spawn, cost 12 wheat)
        spawn_warriors = min(len(remaining_farmers) // 2, wheat_after_farm_spawns // 12)

        # Assign 2*spawn_warriors farmers to the "spawn warrior" group
        to_spawn_warriors = remaining_farmers[:spawn_warriors * 2]
        for f in to_spawn_warriors:
            environment.assign_group(f, 'spawn warrior')

        # Remaining farmers after warrior spawns
        after_warrior_spawns = remaining_farmers[spawn_warriors * 2:]

        # Everyone else (leftover farmers) stay in Village as regular farmers
        for f in after_warrior_spawns:
            environment.assign_group(f, 'farm')

        # Note: Any farmers not explicitly assigned above should be explicitly assigned.
        # If some farmers were not in the initial list due to edge cases, there is nothing else to do.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, we want Warriors to attack and Farmers to go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers should return to Village
                environment.assign_group(c, 'village')
```