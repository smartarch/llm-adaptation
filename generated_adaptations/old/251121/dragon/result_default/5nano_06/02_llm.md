Reasoning and task analysis:
- Objective: Kill the Dragon as fast as possible. The Dragon starts with 50 HP and SDL steps limit of 30. Warriors deal more damage (3) than Farmers (1). Farmers generate wheat, which is needed to spawn more villagers. Spawning rules:
  - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- Constraints:
  - All Warriors should go to the Cave and then attack the Dragon.
  - All Farmers should stay in Village and either farm or spawn new villagers (both Farmer and Warrior spawns are beneficial for scaling DPS).
- In Village:
  - Farmers can be assigned to: farm, spawn farmer, spawn warrior, or cave (not allowed; farmers should stay in village). We’ll avoid assigning farmers to cave.
  - Warriors should be sent to the Cave (they’ll be in Cave and later move to attack in the cave step).
- In Cave:
  - Warriors should be assigned to attack the Dragon.
  - Farmers should go back to the Village (they should not stay in Cave).
- Spawn logic is governed by wheat in the Farm. We should allocate Farm villagers to spawn groups in a way that respects wheat constraints. A simple, safe policy is to maximize warrior spawns first (since Warriors are immediate attackers), then allocate the remaining wheat to farmer spawns, with any leftover farmers going to farming.

 adaptation strategy description:
- In assign_in_village:
  - Move all Warriors to the cave (environment.assign_group(component, 'cave')).
  - For Farmers, determine how many can form spawn-warrior groups (2 farmers per group, consuming 12 wheat per group) and how many can form spawn-farmer groups (2 farmers per group, consuming 10 wheat per group), given current wheat in environment.farm.wheat.
  - We greedily allocate:
    - First, maximum possible warrior spawn pairs (2 farmers per pair, up to floor(wheat/12) and up to floor(num_farmers/2)).
    - Then, with remaining wheat, maximum possible farmer spawn pairs (2 farmers per pair, up to floor((remaining_farmers)/2) and floor(remaining_wheat/10)).
  - The remaining Farmers (if any) stay in the Village to farm (group 'farm').
  - Warriors are not assigned to any spawn group; they stay in cave until assign_in_cave moves them to attack.
- In assign_in_cave:
  - Move all Warriors to the attack group (environment.assign_group(component, 'attack')).
  - Move all Farmers to village (environment.assign_group(component, 'village')) so they can continue farming or spawn from there.

Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in the village by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All Warriors should go to the cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # 2) Allocate farmers to farming / spawning groups based on available wheat
        wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)
        n_farmers = len(farmers)

        # Max number of warrior-spawn groups we can form from farmers given wheat
        max_war_spawns = min(n_farmers // 2, wheat // 12)
        remaining_wheat_after_war = wheat - max_war_spawns * 12

        # Max number of farmer-spawn groups we can form with remaining farmers and wheat
        max_farm_spawns = min((n_farmers - max_war_spawns * 2) // 2, remaining_wheat_after_war // 10)

        # Assign farmers to the appropriate groups:
        # - First 2*max_war_spawns farmers -> spawn warrior
        # - Next 2*max_farm_spawns farmers -> spawn farmer
        # - Remaining farmers -> farm
        for i, f in enumerate(farmers):
            if i < max_war_spawns * 2:
                environment.assign_group(f, 'spawn warrior')
            elif i < max_war_spawns * 2 + max_farm_spawns * 2:
                environment.assign_group(f, 'spawn farmer')
            else:
                environment.assign_group(f, 'farm')

        # Note: If there are no farmers, Warriors have already been sent to cave.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack the Dragon; Farmers return to Village
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```