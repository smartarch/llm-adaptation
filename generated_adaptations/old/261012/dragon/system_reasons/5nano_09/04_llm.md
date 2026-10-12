Reasoning and adaptation strategy

Goal and constraints recap:
- All Warriors must eventually go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (farm or spawn new villagers).
- Spawn rules: For every two villagers assigned to a spawn group and the required wheat (10 for spawn farmer, 12 for spawn warrior), a new Villager is spawned.
- Wheat is produced by Farmers who stay in the Village and farm (5 wheat per Farmer per farming action).
- The Dragon can retaliate and can kill villagers, so population management is important.
- We want the Dragon dead as fast as possible, with an attack at least once within the first 15 steps.

Improved strategy overview:
- Early and steady aggression: Move all Warriors to the Cave as soon as possible so they can join the attack quickly.
- Farming-first balance: Keep at least one Farmer always farming to ensure a steady stream of Wheat for spawning.
- Controlled spawning to accelerate DPS: Spawn new Farmers and Warriors when Wheat allows, but reserve enough Farmers to sustain Wheat production in future steps. Specifically:
  - Use as many Farmers as possible to spawn new Farmers (spawn farmer) without starving Wheat production by leaving at least one Farmer to farm.
  - Use remaining Farmers to spawn Warriors (spawn warrior) when Wheat allows.
- Cave phase: In the Cave, send Warriors to Attack the Dragon and return Farmers to the Village, preserving Farmers in Village as required.
- The plan aims to ensure early Dragon engagement (attack by step 1-2) and rapid population growth to maximize DPS, while keeping enough Wheat production to sustain spawning over multiple steps.

Code implementation
- The updated SmartAdaptation class refines the spawn logic to always keep at least one Farmer farming, while prioritizing spawning to increase DPS in a balanced way.
- In assign_in_village, we compute spawns_farm and spawns_war with safeguards to preserve farming capability.
- In assign_in_cave, we ensure Warriors attack and Farmers return to the Village.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay and farm
        - cave: go to the Cave
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a Warrior
        Strategy:
        - Move all Warriors to the Cave (to attack later).
        - For Farmers, allocate to spawn groups while keeping at least one Farmer farming to ensure wheat production.
        - The rest stay in Farm.
        - This keeps a balance between growing wheat (to enable spawns) and spawning new villagers.
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Wheat available
        wheat = int(getattr(environment.farm, "wheat", 0))

        n_farmers = len(farmers)
        spawns_farm = 0
        spawns_war = 0

        if n_farmers >= 2:
            # Maximum spawns this turn if we only consider farmers to spawn
            max_farm_spawns = min(n_farmers // 2, wheat // 10)

            # Ensure at least one farmer remains farming
            # If we would use up all farmers for spawns, reduce spawns_farm accordingly
            if n_farmers - (2 * max_farm_spawns) < 1:
                max_farm_spawns = max(0, (n_farmers - 1) // 2)

            spawns_farm = max_farm_spawns

            wheat_after_farm = max(0, wheat - spawns_farm * 10)

            # Remaining farmers after earmarking for farming/spawn_farm
            remaining_farmers_after_farm = n_farmers - (spawns_farm * 2)
            if remaining_farmers_after_farm >= 2:
                spawns_war = min(remaining_farmers_after_farm // 2, wheat_after_farm // 12)

        # Assign groups for farmers
        # Order: first 2*spawns_farm to "spawn farmer",
        # next 2*spawns_war to "spawn warrior",
        # the rest to "farm"
        for idx, f in enumerate(farmers):
            if idx < spawns_farm * 2:
                environment.assign_group(f, "spawn farmer")
            elif idx < (spawns_farm * 2) + (spawns_war * 2):
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Assign all Warriors to cave (to move to Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Note: If there are any villagers not covered (unexpected cases), default to staying in farm.
        # This ensures every component is assigned to one of the valid groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy:
        - All Warriors should attack the Dragon, so assign all Warriors to "attack".
        - All Farmers should return to the Village, so assign them to "village".
        - This keeps farmers in the Village and ensures warriors are ready to attack.
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role
                environment.assign_group(c, "cave")
```