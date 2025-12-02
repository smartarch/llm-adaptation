"""
Strategy rationale and adaptation plan

Goal: Kill the Dragon as fast as possible by coordinating villagers (Farmers and Warriors)
through two phases: in Village and in Cave. The Dragon can retaliate, so we must balance
offense with survivability and growth.

Key ideas:
- All Warriors should be sent to the Cave to attack the Dragon as soon as possible.
- Farmers should primarily stay in the Village to farm (generate Wheat) and to spawn
  new villagers when enough Wheat and villager presence are available.
- Spawning rules:
  - spawn farmer: for every two villagers assigned to the "spawn farmer" group and at least
    10 Wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to the "spawn warrior" group and at least
    12 Wheat, a new Warrior is spawned.
  - The engine likely consumes Wheat when spawning; our code should configure groups so the
    game can spawn automatically.
- Practical grouping in Village:
  - Put all Warriors in "cave" to move toward the Dragon.
  - For Farmers, decide how many to dedicate to spawning (spawn farmer and spawn warrior)
    versus farming:
    - Compute possible farmer spawns: X = min(F // 2, Wheat // 10)
    - After reserving Wheat for these spawns, compute possible warrior spawns: Y = min((F - 2*X) // 2, (Wheat - 10*X) // 12)
    - Assign 2*X Farmers to "spawn farmer", 2*Y Farmers to "spawn warrior", and the rest to "farm".
- Cave behavior:
  - All Warriors in Cave should be assigned to "attack" (to actually attack the Dragon).
  - Farmers in Cave should be assigned back to "village" (they should not linger in Cave unless needed for spawn decisions in the village).
- Step-awareness:
  - The above strategy is deterministic per step and aims to maximize early growth while keeping enough Warriors able to attack.

Implementation notes:
- The adaptation is implemented as a class SmartAdaptation deriving from DragonHuntAdaptation.
- assign_in_village distributes the given village villagers into: "farm", "cave", "spawn farmer", "spawn warrior".
- assign_in_cave distributes the cave villagers into: "attack" (for Warriors) and "village" (for Farmers).

Now the Python implementation:

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = len(warriors)

        # Wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Compute how many spawns we can try to trigger this step
        # Each spawn event requires 2 villagers in the spawn group and consuming 10 Wheat (farm) or 12 Wheat (warrior)
        spawn_farmers = min(F // 2, wheat // 10)

        # Wheat left after reserving for farmer spawns
        wheat_left_after_farm = max(0, wheat - spawn_farmers * 10)

        # Spawns for warriors depend on remaining farmers and remaining wheat
        remaining_farmers_for_warrior_spawns = F - spawn_farmers * 2
        spawn_warriors = min(remaining_farmers_for_warrior_spawns // 2, wheat_left_after_farm // 12)

        # Assign all Warriors to go to the Cave (via group "cave")
        for w in warriors:
            environment.assign_group(w, "cave")

        # Assign Farmers to spawn groups and farming
        idx = 0

        # 1) Assign 2*spawn_farmers farmers to "spawn farmer"
        to_spawn_farmers = spawn_farmers * 2
        for _ in range(to_spawn_farmers):
            if idx < F:
                farmers[idx]  # access to keep clarity
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
            else:
                break

        # 2) Assign 2*spawn_warriors farmers to "spawn warrior" from the remaining
        to_spawn_warriors = spawn_warriors * 2
        for _ in range(to_spawn_warriors):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1
            else:
                break

        # 3) Remaining farmers go to "farm" (stay in Village and farm)
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave, Warriors should attack, Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")