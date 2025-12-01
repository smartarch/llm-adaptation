Reasoning and adaptation strategy

Goal and constraints recap:
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in the Village to farm or spawn new villagers (both Farmers and Warriors are needed for a strong push).
- In the Village, we have groups: farm (stay and farm), cave (go to cave), spawn farmer (for every two villagers in this group and 10 wheat, spawn a new Farmer), spawn warrior (for every two villagers in this group and 12 wheat, spawn a new Warrior).
- Spawn decisions depend on available wheat in the Farm and the number of villagers assigned to the corresponding spawn groups.
- In the Cave, we have groups: attack (attack the Dragon), cave (stay in the Cave), village (go back to the Village).
- All Warriors should end up in the Cave and attack, all Farmers should stay in the Village.

Strategy description:
- Village phase (assign_in_village):
  - Move all Warriors to the Cave (group "cave") so they can attack later.
  - For Farmers, allocate some to spawn farmers and some to (regular) farm, based on current wheat.
  - To spawn K farmers, we need 2K farmers assigned to "spawn farmer" and 10K wheat. We compute:
    - Wheat available = environment.farm.wheat
    - K_farmers = min(number_of_farmers // 2, Wheat // 10)
    - Assign 2*K_farmers farmers to "spawn farmer"
  - After that, with the remaining farmers and the remaining Wheat, spawn Warriors if beneficial:
    - For K_warriors, need 2*K_warriors farmers and 12 Wheat, so
      K_warriors = min( (remaining_farmers // 2), Wheat_after_farm // 12 )
      Assign 2*K_warriors farmers to "spawn warrior"
  - The leftover farmers are assigned to "farm" (stay in the Village to farm).
  - This ordering prioritizes spawning when there is Wheat, and uses the remaining farmers to farm, ensuring Farmers stay in Village while Warriors (and spawning) help grow the population.

- Cave phase (assign_in_cave):
  - Move all Warriors to the "attack" group to actively fight the Dragon.
  - Move all Farmers to the "village" group so they return to the Village (as per constraint that Farmers should stay in Village for farming or spawning).

- The implementation ensures every component is assigned to exactly one group, and uses the exact group names required.

Now the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, 'cave')

        # Step 2: Allocate Farmers to farming and spawning
        n_farmers = len(farmers)
        Wheat = getattr(environment.farm, 'wheat', 0)

        # First, determine how many farmers we can spawn as "spawn farmer"
        # Each spawn farmer requires 2 villagers and 10 wheat -> K = min(n_farmers//2, Wheat//10)
        k_farmers = min(n_farmers // 2, Wheat // 10)
        spawn_farmer_count = 2 * k_farmers
        Wheat_after_farmers = Wheat - (10 * k_farmers)

        # Assign the first 2*k_farmers farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            if i < n_farmers:
                environment.assign_group(farmers[i], 'spawn farmer')

        # Remaining farmers after allocating to spawn farmer
        idx = spawn_farmer_count
        remaining_farmers = n_farmers - idx

        # Next, determine how many of the remaining farmers we can use to spawn warriors
        # Each spawn warrior requires 2 villagers and 12 wheat -> K = min(remaining_farmers//2, Wheat_after_farmers//12)
        k_warriors = min(remaining_farmers // 2, Wheat_after_farmers // 12)
        spawn_warrior_count = 2 * k_warriors

        for i in range(spawn_warrior_count):
            if idx + i < n_farmers:
                environment.assign_group(farmers[idx + i], 'spawn warrior')

        idx += spawn_warrior_count
        # The rest of the farmers go to farming in the Village
        for j in range(idx, n_farmers):
            environment.assign_group(farmers[j], 'farm')

        # If there are no farmers, nothing else to do in this step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            elif role == 'Farmer':
                environment.assign_group(c, 'village')
            else:
                # Unknown role: keep safe by sending to Village
                environment.assign_group(c, 'village')
```