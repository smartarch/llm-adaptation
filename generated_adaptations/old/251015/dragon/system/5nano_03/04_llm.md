Reasoning and strategy:
- Goal: Kill the Dragon faster by improving how we spawn villagers and send them to battle.
- Key factors:
  - Warriors deal more damage (3) but must be in the Cave to attack; they are our primary DPS.
  - Spawning is wheat-limited and requires two villagers assigned to a spawn group. Spawning a farmer increases long-term wheat production, while spawning a warrior increases short-term DPS.
  - The Dragon can hurt villagers in the Cave, so we want to balance risk (more villagers in Cave) with reward (more DPS).
- Strategy improvements:
  - Make spawning dynamic and HP-aware. When the Dragon is strong (high HP), prioritize wheat production to enable future spawns. When the Dragon is weak (low HP), push as many Warrior spawns as possible to maximize DPS and end the fight sooner.
  - Keep all Warriors in the Cave (via the Cave/Attack flow) to satisfy the constraint that Warriors must attack the Dragon. Farmers stay in Village to farm or spawn more villagers.
  - In the Village:
    - Always move Warriors to the Cave.
    - For Farmers, decide between spawning more Farmers or spawning Warriors based on current Dragon HP and available wheat:
      - If Dragon HP <= 20: spawn as many Warriors as possible (up to available farmers and wheat) to finish quickly.
      - Otherwise: spawn Farmers first to boost wheat production, then use remaining wheat to spawn Warriors if feasible.
  - In the Cave: send Warriors to Attack; Farmers go to Village (to farm/spawn again).
- This approach aims to shorten the time to kill the Dragon by increasing early DPS when the Dragon is vulnerable, while still building Wheat production for sustained growth.

Python code (SmartAdaptation class):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by current role in the Village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        F = len(farmers)

        # Wheat available for spawning
        wheat = 0
        if hasattr(environment, 'farm') and environment.farm is not None:
            wheat = getattr(environment.farm, 'wheat', 0)

        # Dragon HP to decide spawning priority
        hp = None
        if hasattr(environment, 'dragon') and environment.dragon is not None:
            hp = getattr(environment.dragon, 'hp', None)

        spawns_f = 0
        spawns_w = 0

        # HP-aware spawning strategy
        if hp is not None and hp <= 20:
            # Spawn as many Warriors as possible first to maximize DPS
            spawns_w = min(F // 2, wheat // 12)
            wheat -= spawns_w * 12
            donors_for_w = 2 * spawns_w
            remaining_farmers = F - donors_for_w

            # Then spawn Farmers with remaining wheat
            spawns_f = min(remaining_farmers // 2, wheat // 10)
            wheat -= spawns_f * 10
        else:
            # Balanced/spawn farmers first to grow wheat, then Warriors if possible
            spawns_f = min(F // 2, wheat // 10)
            wheat -= spawns_f * 10
            donors_for_f = 2 * spawns_f
            remaining_farmers = F - donors_for_f

            spawns_w = min(remaining_farmers // 2, wheat // 12)
            wheat -= spawns_w * 12

        # Assign donors for spawn farmer
        idx = 0
        for _ in range(2 * spawns_f):
            if idx < F:
                environment.assign_group(farmers[idx], 'spawn farmer')
                idx += 1

        # Assign donors for spawn warrior
        for _ in range(2 * spawns_w):
            if idx < F:
                environment.assign_group(farmers[idx], 'spawn warrior')
                idx += 1

        # Remaining farmers go to farming
        for i in range(idx, F):
            environment.assign_group(farmers[i], 'farm')

        # All Warriors in Village should head to the Cave
        for w in warriors:
            environment.assign_group(w, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack; Farmers should go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                environment.assign_group(c, 'village')
```