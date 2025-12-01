Reasoning and updated adaptation strategy

Task reality:
- Warriors are the primary damage dealers. All Warriors should go to the Cave to attack the Dragon.
- Farmers are the engine for wheat production and spawning. They stay in the Village to farm and to spawn new villagers when wheat is available.
- Spawning rules: In the Village, you can assign villagers to spawn farmer or spawn warrior groups. For each two villagers assigned to a spawn group and the required wheat (10 for Farmer, 12 for Warrior), one new villager of that type is spawned. You can spawn multiple villagers per turn as long as there are enough villagers and enough wheat (and at least two villagers per spawn unit in the group).

Why the previous approach could be improved:
- It assigned a fixed small number of spawns per turn. This underutilizes wheat and the available farmers, slowing growth and the eventual DPS growth.
- A more aggressive yet safe spawning policy can accelerate growth by prioritizing spawning as many villagers as allowed by current wheat and available farmers, while still keeping all Warriors in the Cave to maximize early Dragon damage.

Improved strategy
- In assign_in_village:
  - Move all Warriors to the Cave (as required).
  - Use a dynamic spawning calculation based on wheat and the number of Farmers:
    - Let nf = number of Farmers in the Village.
    - Let wheat = environment.farm.wheat.
    - Compute how many new Farmers we can spawn: s_f_spawn = min(nf // 2, wheat // 10).
      Each such spawn consumes 2 Farmers and 10 wheat, and creates 1 new Farmer.
    - After reserving Farmers for Farmer spawns, compute remaining Farmers nf_remaining = nf - 2*s_f_spawn.
    - Compute how many new Warriors we can spawn with the remaining Farmers and remaining wheat: s_w_spawn = min(nf_remaining // 2, (wheat - 10*s_f_spawn) // 12).
      Each such spawn consumes 2 Farmers and 12 wheat, and creates 1 new Warrior.
    - Assign the actual villagers to the two spawn groups accordingly (two villagers per spawn unit). Remaining Farmers go to farming ("farm").
  - This allows multiple spawns in a single turn whenever resources permit, accelerating population growth and hence wheat production and future DPS.

- In assign_in_cave:
  - All Warriors stay in "attack" (to fight the Dragon).
  - All Farmers go to "village" (to farm or participate in spawning).

This strategy aims to push early growth aggressively when resources allow, while keeping Warriors focused on eliminating the Dragon as soon as possible.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the cave (to attack the Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        nf = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 2) Aggressive, resource-aware spawning
        # How many Farmers can we spawn this turn?
        s_f_spawn = min(nf // 2, wheat // 10)

        # Wheat left after Farmer spawns
        wheat_left = wheat - s_f_spawn * 10

        # Remaining farmers after allocating for Farmer spawns
        nf_remaining = nf - s_f_spawn * 2

        # How many Warriors can we spawn with the remaining resources
        s_w_spawn = 0
        if nf_remaining >= 2:
            s_w_spawn = min(nf_remaining // 2, wheat_left // 12)

        # Assign farming/spawn groups based on the computed spawn counts
        idx = 0
        # Spawn Farmers: 2 farmers per spawn unit in "spawn farmer"
        for _ in range(s_f_spawn):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # Spawn Warriors: 2 farmers per spawn unit in "spawn warrior"
        for _ in range(s_w_spawn):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # Remaining farmers (not used in spawns) go to farming
        while idx < nf:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```