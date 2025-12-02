Reasoning and adaptation strategy

Task analysis:
- There are farmers (HP 4, wheat 5 when farming, damage 1 when attacking) and warriors (HP 6, wheat 2 when farming, damage 3 when attacking).
- You win by killing the Dragon (Dragon HP starts at 50). You lose if you run out of time (30 steps) or all villagers die.
- Spawning new villagers uses two villagers in a spawn group plus a wheat threshold (10 for farmers, 12 for warriors).
- All warriors should go to the Cave and attack the Dragon; all farmers should stay in the Village (though some farming and spawning is allowed).
- The Dragon can attack back: it may damage all villagers in the Cave or eat one random villager in the Cave.
- You want to attack early (at least once within the first 15 steps) and keep a majority of Warriors in the Cave to enable frequent attacks.

Adaptation strategy (description):
- Village assignments:
  - Move all Warriors from the Village to the Cave (group "cave"), so they will eventually attack the Dragon.
  - Farmers stay in the Village as the base strategy (group "farm").
  - Use spawning groups to create new villagers:
    - "spawn farmer": For every 2 villagers assigned to this group and at least 10 wheat in the Farm, spawn a new Farmer.
    - "spawn warrior": For every 2 villagers assigned to this group and at least 12 wheat in the Farm, spawn a new Warrior.
  - Impose a cautious spawning approach:
    - Determine how many spawns are possible given the current wheat (farm.wheat) and the number of available farmers.
    - Allocate 2 farmers per possible spawn for farmers first; allocate additional pairs for warriors if there is sufficient wheat and farmers left.
  - If there are no Warriors in the village to begin with, still spawn at least one Warrior soon by using the "spawn warrior" group if there are at least 2 farmers and 12 wheat available. This helps ensure an early attack.

- Cave assignments:
  - In the Cave, assign all Warriors to the "attack" group so they attack the Dragon.
  - Move Farmers in the Cave back to the Village (group "village") to keep farmers in the agricultural cycle in the Village.
  - If there are no Warriors in the Cave (edge case), ensure at least one farmer is assigned to "attack" to guarantee an attack occurs early (fallback).

- Rationale for constraints:
  - All Warriors should attack and stay in the Cave most of the time (to sustain attempts to kill the Dragon).
  - At least a few new farmers and a few new warriors should spawn to increase DPS and sustain production of wheat.
  - Early attacks are encouraged by ensuring that there is at least one attacker in the Cave by step 2 or 3.

Code (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in the Village and farm
        - cave: go to the Cave (for Warriors)
        - spawn farmer: to spawn new Farmers
        - spawn warrior: to spawn new Warriors
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers stay in Village by default
        # We'll decide on spawning based on available wheat
        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawns we can attempt
        spawns_farmers = 0
        if len(farmers) >= 2 and farm_wheat >= 10:
            spawns_farmers = min(len(farmers) // 2, farm_wheat // 10)

        # Allocate farmers to spawn groups first, then remaining to farm
        idx = 0
        # Assign 2*spawns_farmers villagers to "spawn farmer"
        for _ in range(spawns_farmers * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers (not used for spawning) go to farming or next spawn group
        remaining_farmers = farmers[idx:]

        spawns_warriors = 0
        if len(remaining_farmers) >= 2 and farm_wheat >= 12:
            spawns_warriors = min(len(remaining_farmers) // 2, farm_wheat // 12)

        for _ in range(spawns_warriors * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # The rest of the farmers go to farming
        for f in farmers[idx:]:
            environment.assign_group(f, "farm")

        # Note: Warriors were already sent to the cave above. No explicit assignment to "cave" here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Separate by role
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # All Warriors should attack the Dragon
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Farmers should go back to the Village (to keep farming)
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # Fallback: if there are no Warriors in the Cave, ensure at least one attacker exists
        if len(warriors_in_cave) == 0 and len(farmers_in_cave) > 0:
            environment.assign_group(farmers_in_cave[0], "attack")
            for f in farmers_in_cave[1:]:
                environment.assign_group(f, "village")

```