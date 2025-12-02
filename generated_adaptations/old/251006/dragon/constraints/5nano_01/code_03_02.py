"""
Reasoning and adaptation strategy:
- Primary goal: minimize damage to fields by keeping as many villagers as possible in the Village and
  limiting the number of villagers in the Cave at any time.
- Must still spawn enough Warriors to reliably bring down the Dragon, and spawn Farmers to sustain wheat production.
- Dynamic adaptation: use Dragon HP to decide how aggressively to spawn Warriors.
  - If the Dragon is strong (high HP), spawn as many Warriors as possible to accelerate victory.
  - If the Dragon is weaker (low HP), conserve wheat and farmers for farming/spawning rather than mass Warrior spawns, to keep field damage low and sustain wheat production.
- Spawning rules (in village):
  - You can spawn Warriors with the "spawn warrior" group for every 2 Farmers you allocate to that group and 12 wheat total.
  - You can spawn Farmers with the "spawn farmer" group for every 2 Farmers you allocate to that group and 10 wheat total.
  - Remaining Farmers go to the regular "farm" group.
- In cave:
  - All Warriors should go to the Cave and then attack the Dragon (via the "attack" group in assign_in_cave).
  - Farmers should stay in the Village (via "village" group in assign_in_cave).
- Implementation notes:
  - Reads wheat robustly from environment.farm.wheat.
  - Uses a simple, deterministic policy to bias Warrior spawns when the Dragon HP is high, and bias Farmer spawns when the Dragon HP is low.
  - Ensures every component is assigned to exactly one group per phase.

"""
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Safely read available wheat from the farm
        wheat = 0
        farm = getattr(environment, 'farm', None)
        if farm is not None:
            wheat = getattr(farm, 'wheat', 0)

        # Dragon HP may influence strategy
        dragon_hp = getattr(getattr(environment, 'dragon', None), 'hp', 0)

        # Compute how many warrior spawns we can attempt: need 2 farmers per spawn and 12 wheat per spawn
        Y_max = min(len(farmers) // 2, wheat // 12) if wheat >= 0 else 0

        # Bias strategy by Dragon HP:
        # - If Dragon HP is high, spawn as many warriors as possible.
        # - If Dragon HP is low, conserve a bit and spawn one fewer warrior if possible.
        if dragon_hp > 25:
            Y = Y_max
        else:
            Y = max(0, Y_max - 1)

        # After allocating warrior spawns, compute how many farmer-spawns we can do with remaining resources
        rem_farmers = len(farmers) - 2 * Y
        rem_wheat = wheat - 12 * Y
        X = min(rem_farmers // 2, rem_wheat // 10) if rem_wheat >= 0 else 0

        idx = 0
        # Assign 2*Y farmers to the "spawn warrior" group
        for _ in range(2 * Y):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn warrior')
                idx += 1

        # Assign 2*X farmers to the "spawn farmer" group
        for _ in range(2 * X):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn farmer')
                idx += 1

        # Remaining farmers go to the regular farming group
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], 'farm')

        # All Warriors should go to the Cave (cave group) so they can attack
        for w in warriors:
            environment.assign_group(w, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers in cave should head back to Village to farm/spawn
                environment.assign_group(c, 'village')