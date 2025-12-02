Reasoning and adaptation strategy

Goal recap:
- All Warriors should move to the Cave and then attack the Dragon.
- All Farmers should stay in the Village.
- Spawn mechanics exist to create more Farmers and Warriors, using pairs of villagers and required wheat.
- We want to ensure the Dragon is attacked (at least once in the first 15 steps) and that we have enough Warriors and Farmers to increase the chance of killing the Dragon.
- We should keep a majority of Warriors in the Cave to attack; but we also need to spawn new units to strengthen the army.

Strategy description:
- Village phase (assign_in_village):
  - All current Warriors should be sent to the Cave (group "cave") to move toward attacking the Dragon.
  - Farmers should primarily stay in the Village (group "farm"), but we also use a portion of Farmers to trigger spawns to increase our numbers:
    - Spawn Farmer group: use 2 Farmers per new Farmer to be spawned, consuming 10 wheat per new Farmer. This keeps Farmers in the village and increases the number of Farmers over time.
    - Spawn Warrior group: use 2 Farmers per new Warrior to be spawned, consuming 12 wheat per new Warrior. This avoids pulling Warriors away from cave immediately and ensures we can grow the army with additional Warriors.
  - The actual spawning is performed by assigning the chosen Farmers to the spawn groups ("spawn farmer" and "spawn warrior") according to available Wheat in the Farm environment. The number of new villagers spawned is determined by the rule: for every 2 villagers assigned to a spawn group and the corresponding wheat, one new unit (Farmer or Warrior) is spawned.
  - Any farmers not used for spawning are assigned to the "farm" group (staying in Village).

- Cave phase (assign_in_cave):
  - All Warriors currently present in the Cave should be assigned to the "attack" group to actually attack the Dragon.
  - All Farmers in the Cave should be sent back to the Village, i.e., assigned to the "village" group, since Farmers must stay in the Village.

Why this satisfies requirements:
- All warriors are moved to the cave and then attack the Dragon (assured by assign_in_cave).
- All farmers stay in the Village, except the ones used to spawn, who stay in the Village as well (spawn groups are still in Village).
- We spawn both Farmer and Warrior units as wheat allows, ensuring a growth in both farmer and warrior populations.
- The Dragon is attacked as soon as there are Warriors in the Cave (the attack happens in the cave phase).
- We aim to have new Warriors spawned to keep a strong force, with at least some Warriors in cave to attack.
- At least half of the warriors should be in the Cave most of the time: we keep current Warriors in cave and then in cave phase move them to attack; practically, this keeps a strong presence in the Cave to attack.

Code: Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the cave (group "cave").
        - Farmers stay in village (group "farm") by default.
        - Spawn farmers and/or warriors using the two spawn groups, based on available wheat and the number of farmers.
        - For spawning:
            - To spawn k new Farmers: assign 2k Farmers to "spawn farmer" and consume 10k Wheat.
            - To spawn m new Warriors: assign 2m Farmers to "spawn warrior" and consume 12m Wheat.
        - The remaining Farmers go to the "farm" group.
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn planning: decide how many to spawn, constrained by available farmers and wheat
        f_count = len(farmers)

        # Max possible farmer spawns given number of farmers (need 2 per new farmer) and wheat (10 per new)
        max_farm_spawns = 0
        if f_count >= 2 and wheat >= 10:
            max_farm_spawns = min(f_count // 2, wheat // 10)

        # After allocating farmer-spawn, compute remaining wheat and farmers
        spawn_farm_n = max_farm_spawns  # number of new farmers to attempt to spawn
        wheat_after_farm = wheat - (spawn_farm_n * 10)
        remaining_farmers_after_farm_spawns = f_count - (spawn_farm_n * 2)

        # Max possible warrior spawns: need 2 farmers per new warrior, and 12 wheat per new
        max_war_spawns = 0
        if remaining_farmers_after_farm_spawns >= 2 and wheat_after_farm >= 12:
            max_war_spawns = min(remaining_farmers_after_farm_spawns // 2, wheat_after_farm // 12)

        spawn_war_n = max_war_spawns  # number of new warriors to spawn
        wheat_after_war = wheat_after_farm - (spawn_war_n * 12)

        # Assign groups:
        # 1) Warriors go to cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers allocations for spawning or farming
        used_for_farm_spawns = set()
        used_for_war_spawns = set()

        # Assign first 2*spawn_farm_n farmers to "spawn farmer"
        if spawn_farm_n > 0:
            to_spawn_farm = farmers[:2 * spawn_farm_n]
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            used_for_farm_spawns.update(to_spawn_farm)

        # Assign next 2*spawn_war_n farmers to "spawn warrior" (if any)
        if spawn_war_n > 0:
            start = 2 * spawn_farm_n
            end = start + (2 * spawn_war_n)
            to_spawn_war = farmers[start:end]
            for c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")
            used_for_war_spawns.update(to_spawn_war)

        # The remaining farmers go to farming in village
        for c in farmers:
            if c in used_for_farm_spawns or c in used_for_war_spawns:
                continue
            environment.assign_group(c, "farm")

        # Any non-Farmer, non-Warrior components: stay in village (default to farm)
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors should attack the Dragon: assign to "attack".
        - Farmers should go back to the Village: assign to "village".
        """
        for v in components:
            role = getattr(v, "role", None)
            if role == "Warrior":
                environment.assign_group(v, "attack")
            else:
                # Farmers and any other roles go to the Village
                environment.assign_group(v, "village")
```