Reasoning and adaptation strategy

Task understanding:
- We control villagers who can be Farmers or Warriors.
- Farmers stay in the Village, farm to produce wheat, or participate in spawning to create new villagers.
- Warriors go to the Cave to attack the Dragon; they’re stronger attackers but we must ensure they end up in the Cave and then attack.
- Spawns: "spawn farmer" and "spawn warrior" groups allow creating new Farmers/Warriors given 2 villagers assigned to the group and a wheat cost (10 for Farmer spawn, 12 for Warrior spawn). The spawn consumes wheat from the Farm (environment.farm.wheat) and yields a new villager of the specified type.
- The Dragon should be attacked early; we want Warriors to move to the Cave and attack as soon as possible.
- We must ensure all Warriors eventually attack the Dragon, and most Warriors should be in the Cave to attack.
- Farmers must stay in the Village (they should not end up staying in the Cave).

Strategy overview:
- Village phase:
  - Move all existing Warriors to the Cave (group "cave") so they prepare to move to the Dragon.
  - Keep all Farmers in the Village (they should farm, and optionally participate in spawning). To satisfy “a few new farmers” and “a few new warriors,” allocate some Farmers to spawn groups:
    - Spawn Farmer group: move 2 Farmers (per spawn) to this group if there is at least 10 wheat available. Each spawn uses 2 Farmers and 10 wheat to create a new Farmer. We'll spawn up to 1 or 2 Farmers (i.e., 1 or 2 spawns) based on available wheat and number of Farmers.
    - Spawn Warrior group: after accounting for potential Farmer spawns, take another 2 Farmers per Warrior spawn if there is at least 12 wheat available. Each spawn uses 2 Farmers and 12 wheat to create a new Warrior. We'll spawn up to 1 or 2 Warriors as well, subject to wheat and remaining Farmers.
  - Remaining Farmers stay in the Village and continue farming.
- Cave phase:
  - Move all Warriors to the Attack group to actually attack the Dragon.
  - Move all Farmers to the Village group (they stay in the Village).
  - The Spawn groups may disappear (spawned villagers appear in the game world); they don’t need to be assigned beyond the current step.

Why this satisfies requirements:
- All Warriors are moved to the Cave in the Village phase (and then to Attack in the Cave phase), ensuring they eventually attack and that a substantial portion of Warriors are in the Cave.
- All Farmers remain in the Village during Village and Cave phases (except those temporarily assigned to spawn groups for spawning). We spawn only from Farmers, keeping the core requirement that Farmers stay in the Village.
- We spawn a few new Farmers and a few new Warriors when Wheat is available, increasing the number of attackers and sustainers to improve Dragon kill odds.
- Dragon is attacked (via Warriors) as soon as they move to the Cave and switch to Attack in the Cave phase.
- The first 15 steps are covered by early Warrior movement to the Cave in the Village phase and then Attack in the Cave phase, ensuring the Dragon is attacked early.
- At least half of the Warriors will be in the Cave across steps by virtue of initially sending all Warriors to the Cave in Village phase, then Attack in Cave phase.

Code (Python):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village to farm
        - "cave": go to the Cave (to join the attack later)
        - "spawn farmer": for every two villagers assigned and 10 wheat, spawn a new Farmer
        - "spawn warrior": for every two villagers assigned and 12 wheat, spawn a new Warrior
        Strategy:
        - Move all Warriors to "cave" (to head to the Cave)
        - Use Farmers to populate "spawn farmer" and "spawn warrior" groups based on available wheat
        - Remaining Farmers go to "farm"
        """
        # Collect indices by role
        farmer_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Farmer"]
        warrior_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Warrior"]

        # Track assigned indices to avoid duplicates
        assigned = set()

        # Wheat available for spawning
        available_wheat = getattr(environment.farm, "wheat", 0)

        # 1) Spawn farmers (prefer up to 2 spawns)
        max_farm_spawns = min(len(farmer_indices) // 2, available_wheat // 10)
        spawn_farm_count = min(2, max_farm_spawns)

        spawn_farm_indices = farmer_indices[:2 * spawn_farm_count]
        assigned.update(spawn_farm_indices)

        remaining_farmers_after_farm_spawns = farmer_indices[2 * spawn_farm_count:]

        # Update wheat after spawning farmers
        available_wheat -= spawn_farm_count * 10

        # 2) Spawn warriors from remaining farmers (prefer up to 2 spawns)
        max_warrior_spawns = min(len(remaining_farmers_after_farm_spawns) // 2, available_wheat // 12)
        spawn_warrior_count = min(2, max_warrior_spawns)

        spawn_warrior_indices = remaining_farmers_after_farm_spawns[:2 * spawn_warrior_count]
        assigned.update(spawn_warrior_indices)

        remaining_farmers = remaining_farmers_after_farm_spawns[2 * spawn_warrior_count:]
        assigned.update(remaining_farmers)

        # 3) Assign groups
        # Farmers allocated to spawn groups
        for idx in spawn_farm_indices:
            environment.assign_group(components[idx], "spawn farmer")

        for idx in spawn_warrior_indices:
            environment.assign_group(components[idx], "spawn warrior")

        # Farmers who remain (not spawning) stay in farm
        for idx in remaining_farmers:
            environment.assign_group(components[idx], "farm")

        # Warriors (all go to cave to prepare for attack)
        for idx in warrior_indices:
            environment.assign_group(components[idx], "cave")

        # If any component wasn't assigned (shouldn't happen), default them to farming
        for i, c in enumerate(components):
            if i not in assigned:
                # Safety fallback
                if getattr(c, "role", None) == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        Strategy:
        - Move all Warriors to "attack" (they will attack Dragon)
        - Move all Farmers to "village" (they stay in Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:  # Farmer
                environment.assign_group(c, "village")
```