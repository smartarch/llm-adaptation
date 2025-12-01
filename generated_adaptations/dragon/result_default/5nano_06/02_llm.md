Reasoning and strategy

Goal: Kill the Dragon as fast as possible. Warriors must go to the Cave and attack to maximize damage per step, while Farmers stay in the Village to farm and/or spawn new villagers to bolster the force. Spawning is constrained by wheat and by having pairs of villagers in the spawn groups.

Key points guiding the strategy:
- All Warriors should be assigned to the Cave’s attack path to maximize DPS against the Dragon.
- Farmers should remain in the Village to farm (to generate wheat) and to spawn new Farmers or Warriors when there is enough wheat.
- Spawning rules: For every two villagers in a spawn group, and with enough wheat (10 for a Farmer-spawn, 12 for a Warrior-spawn), a new villager is spawned. The two villagers forming the pair are the ones assigned to that spawn group; no special removal of those villagers is assumed here, they just enable spawning if the wheat constraint is met.
- To ensure wheat is available for spawning, keep at least one farmer farming in the Village; other farmers can be allocated to spawning groups as wheat allows.
- In the cave, Farmers are better kept in the Village (as per the requirement), so in Cave, Farmers should be moved to the Village group, while Warriors go to Attack.

Adaptation strategy (high level):
- assign_in_village:
  - Move all Warriors to the cave (Attack group for this step) or rather to the cave spawn decision: the Warriors will be assigned to the cave’s Attack group in the cave step; in village step, we decide where to place Warriors who are still in village (but the rule says all Warriors should end up in Cave to attack). For simplicity and clarity, we place all Warriors into the "cave" group in village step to reflect they are heading to Cave for attack, while Farmers remain in Village.
  - Among Farmers:
    - Reserve at least 1 Farmer for farming (group "farm") to produce wheat.
    - With the remaining Farmers, allocate some to "spawn farmer" and some to "spawn warrior" based on available wheat:
      - spawns_f = min(floor(remaining_farmers / 2), floor(W / 10))
      - Wheat left after spawns_f: W' = W - spawns_f * 10
      - spawns_w = min(floor((remaining_farmers - 2*spawns_f) / 2), floor(W' / 12))
    - The rest of the Farmers go to "farm" (stay in Village).
    - Assign Farmers in a deterministic order to: farm, spawn farmer, spawn warrior.
  - This keeps at least one farmer farming to accumulate wheat, and uses available wheat to spawn more villagers when beneficial.

- assign_in_cave:
  - Warriors go to the Attack group (to actually attack the Dragon).
  - Farmers go to the Village group (they should return to the Village to farm or spawn).

The implementation below follows this plan. It uses environment.assign_group(component, group_id) to place components in the specified groups.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify farmers and warriors in this village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default group names (must be exactly as expected)
        farm_gid = "farm"
        spawn_f_gid = "spawn farmer"
        spawn_w_gid = "spawn warrior"
        cave_gid = "cave"

        # Ensure groups exist in the provided list (robustness)
        if farm_gid not in group_ids:
            farm_gid = None
        if spawn_f_gid not in group_ids:
            spawn_f_gid = None
        if spawn_w_gid not in group_ids:
            spawn_w_gid = None
        if cave_gid not in group_ids:
            cave_gid = None

        # If there are no farmers at all, nothing to spawn, just keep things simple
        W = 0
        try:
            W = int(getattr(environment.farm, "wheat", 0) or 0)
        except Exception:
            W = 0

        # If there are no farmers, just ensure all villagers are assigned to a sane default
        if not farmers:
            # All villagers (if any) should go to cave if they are warriors; otherwise to farm
            for c in components:
                if getattr(c, "role", None) == "Warrior" and cave_gid is not None:
                    environment.assign_group(c, cave_gid)
                elif farm_gid is not None:
                    environment.assign_group(c, farm_gid)
            return

        # Reserve at least one farmer for farming (to generate wheat)
        total_farmers = len(farmers)
        reserve_for_farm = 1 if total_farmers >= 1 else 0

        remaining_farmers = total_farmers - reserve_for_farm

        # Compute spawns based on wheat and available farmers
        spawns_f = 0
        spawns_w = 0

        if remaining_farmers > 0 and W > 0:
            spawns_f = min(remaining_farmers // 2, W // 10)
            W_after_f = W - spawns_f * 10
            remaining_after_f = remaining_farmers - (spawns_f * 2)
            if remaining_after_f > 0 and W_after_f > 0:
                spawns_w = min(remaining_after_f // 2, W_after_f // 12)

        k_f = spawns_f * 2  # farmers allocated to spawn farmer group
        k_w = spawns_w * 2  # farmers allocated to spawn warrior group

        # Number of farmers left to farm
        farm_count = total_farmers - reserve_for_farm - k_f - k_w
        if farm_count < 0:
            farm_count = 0

        # Build assignment plan for farmers in order
        # Order: [farmers for farm] then [farmers for spawn farmer] then [farmers for spawn warrior]
        # We'll assign deterministically based on the list order
        idx = 0
        # 1) assign to farm
        for i in range(farm_count):
            if farm_gid is not None:
                environment.assign_group(farmers[idx], farm_gid)
            idx += 1

        # 2) assign to spawn farmer
        for i in range(spawns_f):
            if spawn_f_gid is not None:
                environment.assign_group(farmers[idx], spawn_f_gid)
            idx += 1

        # 3) assign to spawn warrior
        for i in range(spawns_w):
            if spawn_w_gid is not None:
                environment.assign_group(farmers[idx], spawn_w_gid)
            idx += 1

        # 4) remaining farmers (if any) go to farm
        while idx < total_farmers:
            if farm_gid is not None:
                environment.assign_group(farmers[idx], farm_gid)
            idx += 1

        # Warriors: all go to cave (to attack)
        if cave_gid is not None:
            for w in warriors:
                environment.assign_group(w, cave_gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should Attack; Farmers should go back to Village
        attack_gid = "attack"
        cave_gid = "cave"
        village_gid = "village"

        # Validate group presence
        if attack_gid not in group_ids:
            attack_gid = None
        if cave_gid not in group_ids:
            cave_gid = None
        if village_gid not in group_ids:
            village_gid = None

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior" and attack_gid is not None:
                environment.assign_group(c, attack_gid)
            elif role == "Farmer" and village_gid is not None:
                environment.assign_group(c, village_gid)
            else:
                # Fallback: keep current in cave or farm back to village if possible
                if village_gid is not None:
                    environment.assign_group(c, village_gid)
                elif cave_gid is not None:
                    environment.assign_group(c, cave_gid)
```