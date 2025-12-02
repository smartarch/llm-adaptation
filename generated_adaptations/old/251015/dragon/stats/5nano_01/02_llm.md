```py
# Strategy reasoning (embedded as comments for clarity)
# Task summary:
# - We control villagers (Farmers and Warriors) to defeat a Dragon ASAP.
# - Farmers: HP 4, farming yields 5 wheat, attacking yields 1 damage.
# - Warriors: HP 6, farming yields 2 wheat, attacking yields 3 damage.
# - Spawn logic: To spawn a new Villager, at least two villagers must be in a spawn group and
#   there must be enough wheat: 10 wheat for a Farmer, 12 wheat for a Warrior.
# - Dragon: HP 50, can retaliate; we must defeat within 30 steps.
#
# Strategy outline:
# - All Warriors should go to the Cave and then attack the Dragon.
# - All Farmers stay in the Village to farm or spawn new villagers.
# - We will opportunistically spawn new Farmers and Warriors if there is enough wheat, to
#   bolster future DPS and sustain the push against the Dragon.
# - Group plan:
#   - In village:
#     - Warriors -> group "cave" (to go to cave) initially, but in the cave phase they must be in "attack".
#     - Farmers -> group "farm" by default.
#     - If wheat >= 10 and at least two Farmers exist, designate two Farmers to "spawn farmer" to spawn a new Farmer.
#     - If after that there are at least two remaining Farmers and wheat >= 12, designate two more Farmers to
#       "spawn warrior" to spawn a new Warrior.
#     - This keeps Farmers in Village (farming) and gradually grows the force with new villagers.
#   - In cave:
#     - Warriors -> "attack" (they will attack the Dragon).
#     - Farmers present in the cave (due to some edge cases) -> send back to Village with "village".
# - This approach ensures the policy constraint (all Warriors go to cave and attack) while keeping Farmers active in the Village for farming and spawning.
#
# Implementation notes:
# - We explicitly re-assign every component to a group on each call, satisfying the "explicit re-assignment"
#   requirement even when a component would conceptually stay in the same action.
# - We use environment.farm.wheat to gate spawning decisions.
# - We keep the logic simple and deterministic (based on current wheat and counts).

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants (must match required strings)
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave (to move to cave); Farmers stay in farm by default.
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Step 2: Spawn farmer if possible (need two farmers and at least 10 wheat)
        spawn_farm_candidates = farmers[:2] if len(farmers) >= 2 else []
        if len(spawn_farm_candidates) == 2 and getattr(environment, "farm", None) is not None:
            wheat = environment.farm.wheat
            if wheat >= 10:
                # Move the first two farmers into the spawn farmer group
                for c in spawn_farm_candidates:
                    environment.assign_group(c, SPAWN_FARMER)
                remaining_farmers = farmers[2:]
                # Step 3: Optionally spawn warriors if wheat allows and we have two spare farmers
                if len(remaining_farmers) >= 2 and environment.farm.wheat >= 12:
                    # Move two of the remaining farmers to spawn warrior
                    to_spawn_warrior = remaining_farmers[:2]
                    for c in to_spawn_warrior:
                        environment.assign_group(c, SPAWN_WARRIOR)
                    # The rest stay farming
                    for c in remaining_farmers[2:]:
                        environment.assign_group(c, FARM)
                else:
                    # Not enough wheat or not enough farmers to spawn warriors; keep rest farming
                    for c in remaining_farmers:
                        environment.assign_group(c, FARM)
            # If wheat < 10, skip spawning entirely and keep all farmers farming
        # If less than 2 farmers, there is nothing to spawn; all farmers stay farming (already assigned)

        # Note: Warriors have already been directed to "cave" above; additional spawn-related
        # logic could continue in subsequent steps as wheat grows.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors in cave should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in cave should return to the village
                environment.assign_group(c, VILLAGE)

        # Note: If there are any Farmers in the cave due to edge cases, they are moved to village,
        # ensuring the policy "Farmers stay in Village" is respected.
```