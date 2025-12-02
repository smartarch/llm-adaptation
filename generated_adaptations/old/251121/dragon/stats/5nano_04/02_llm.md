Reasoning and adaptation strategy:
- Objective: Kill the Dragon as fast as possible while ensuring villagers survive and wheat is used to spawn more villagers when advantageous.
- Core idea: 
  - All Warriors should head to the Cave to attack the Dragon as soon as possible.
  - Farmers should stay in the Village to farm and generate wheat, and also organize spawns to grow the population when wheat is available.
  - Use a simple, deterministic spawning strategy:
    - Reserve a couple of Farmers to keep farming (to produce wheat).
    - From the remaining Farmers, allocate some to spawn new Farmers and/or Warriors, using 2 Farmers per spawn and consuming 10 Wheat (for a new Farmer) or 12 Wheat (for a new Warrior) per spawn event.
    - Prefer spawning Warriors first if there is sufficient Wheat, then spawn Farmers, constrained by available villagers and Wheat.
- In the Cave, keep it simple: Warriors in Cave will Attack the Dragon; Farmers in Cave will Return to Village (since Farmers should stay in Village).
- The strategy respects the required group names:
  - Village: farm, cave, spawn farmer, spawn warrior
  - Cave: attack, cave, village
- Rationale:
  - Attacking early increases damage to the Dragon; with multiple Warriors, you can threaten a quick kill if you manage to keep them alive.
  - Spawning more villagers increases long-term DPS and Wheat production, enabling faster dragon takedown if Wheat is sufficient and casualties are manageable.
  - Farming Farmers in Village maintains Wheat supply, which is the key resource to enable spawns.

Code (Python):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) != 'Farmer']

        # 1) Send all Warriors to the Cave to prepare for attack
        for c in warriors:
            environment.assign_group(c, 'cave')  # they travel to cave

        # 2) Divide Farmers into farming and spawning roles
        F = len(farmers)

        # Reserve a couple of farmers for farming (to keep Wheat production stable)
        reserved_for_farm = min(2, F)

        # Remaining farmers are candidates for spawning
        remaining = farmers[reserved_for_farm:]

        # Wheat available for spawning decisions (safe access)
        wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, 'wheat', 0)

        # Spawning plan: attempt to spawn as many as possible given Wheat
        i = 0
        # First, spawn Warriors (2 farmers needed per Warrior, cost 12 Wheat)
        while i + 1 < len(remaining) and wheat >= 12:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn warrior')
            environment.assign_group(b, 'spawn warrior')
            wheat -= 12
            i += 2

        # Next, spawn Farmers (2 farmers needed per Farmer, cost 10 Wheat)
        while i + 1 < len(remaining) and wheat >= 10:
            a = remaining[i]
            b = remaining[i + 1]
            environment.assign_group(a, 'spawn farmer')
            environment.assign_group(b, 'spawn farmer')
            wheat -= 10
            i += 2

        # Any leftover farmers go to farming
        while i < len(remaining):
            environment.assign_group(remaining[i], 'farm')
            i += 1

        # Ensure reserved farming farmers are in the farming group
        for idx in range(reserved_for_farm):
            environment.assign_group(farmers[idx], 'farm')

        # Note: All Farmers in this step are assigned to either 'farm', 'spawn farmer', or 'spawn warrior'.
        # Warriors are already assigned to the cave (as per strategy).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack the Dragon; Farmers should go back to Village.
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```