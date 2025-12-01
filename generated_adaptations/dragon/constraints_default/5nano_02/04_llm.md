Reasoning and updated adaptation strategy

What changed and why:
- The tests require that we spawn a few new Warriors to improve the chance of killing the Dragon. Our previous strategy prioritized spawning Farmers first, which could starve the ability to spawn Warriors when wheat and farmer counts allow both. This reduced the number of new Warriors spawned and led to failures.
- New strategy: prioritize spawning Warriors first, then spawn Farmers with any remaining wheat and farmers. This ensures we generate at least some new Warriors whenever resources allow, while still leveraging remaining farmers to spawn additional Farmers or farm.
- In the village phase:
  - Move all existing Warriors to the Cave (so they can attack later).
  - With the current number of Farmers (F) and Wheat (W in the farm), spawn as many Warriors as possible: sw = min(F // 2, W // 12).
  - After dedicating 2*sw Farmers to spawn Warriors, use the remaining Farmers and Wheat to spawn Farmers: sf = min((F - 2*sw) // 2, (W - 12*sw) // 10).
  - Assign the remaining Farmers to farming in the Village.
- In the cave phase, keep Warriors attacking the Dragon and Farmers going back to the Village.

This strategy ensures:
- Warriors are spawned whenever possible, increasing offensive power early.
- Farmers continue to be useful for farming and potential additional spawns with leftover wheat.
- All components are assigned to exactly one group per step, respecting the required group names.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All existing Warriors go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, 'cave')

        F = len(farmers)
        W = getattr(environment.farm, 'wheat', 0)

        # Step 2: Spawn as many Warriors as possible:
        # Each Warrior spawn requires 2 Farmers and 12 Wheat
        sw = 0
        if F >= 2 and W >= 12:
            sw = min(F // 2, W // 12)

        # Update remaining farmers and wheat after spawning warriors
        F_rem = F - 2 * sw
        W_rem = W - 12 * sw

        # Step 3: With remaining resources, spawn as many Farmers as possible
        sf = 0
        if F_rem >= 2 and W_rem >= 10:
            sf = min(F_rem // 2, W_rem // 10)

        # Assign groups for farmers:
        # First, assign 2*sw farmers to 'spawn warrior'
        for i in range(2 * sw):
            if i < F:
                environment.assign_group(farmers[i], 'spawn warrior')

        # Next, assign 2*sf farmers to 'spawn farmer'
        offset = 2 * sw
        for i in range(2 * sf):
            if offset + i < F:
                environment.assign_group(farmers[offset + i], 'spawn farmer')

        # Remaining farmers go to farming in the Village
        offset2 = offset + 2 * sf
        for i in range(offset2, F):
            environment.assign_group(farmers[i], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            elif role == 'Farmer':
                environment.assign_group(c, 'village')
            else:
                environment.assign_group(c, 'village')
```