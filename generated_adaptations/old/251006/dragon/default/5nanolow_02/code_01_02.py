from __future__ import annotations
import abc

# Assuming the base class is available from the specified module
# from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class DragonHuntAdaptation(abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def assign_in_village(self, components, environment, group_ids, step: int):
        pass

    @abc.abstractmethod
    def assign_in_cave(self, components, environment, group_ids, step: int):
        pass


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - "farm": Farmers farming in village
        - "cave": Farmers/Warriors going to Cave (Warriors only)
        - "spawn farmer": Pairs of Farmers spawn new Farmers (consume 10 wheat)
        - "spawn warrior": Pairs of Farmers spawn new Warriors (consume 12 wheat)
        Note: All Warriors should go to the Cave (not spawned here). Farmers may spawn new villagers.
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Fetch current wheat from farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Start by assigning Everyone to default positions
        # Warriors are sent to Cave (they will be moved there below)
        for c in components:
            # Warriors go to cave
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            else:
                # Farmers will be assigned to farm or spawn groups
                environment.assign_group(c, "farm")

        # Now decide spawning from Farmers only (since all Warriors must stay/Cave)
        # We can form up to floor(len(farmers)/2) spawn pairs, limited by wheat/10
        max_farm_spawns = len(farmers) // 2
        possible_spawns_by_wheat = wheat // 10
        spawn_farmers_pairs = min(max_farm_spawns, possible_spawns_by_wheat)

        # Move 2 * spawn_farmers_pairs farmers from "farm" to "spawn farmer"
        if spawn_farmers_pairs > 0:
            moved = 0
            for c in farmers:
                # Find those currently in "farm" group
                if getattr(c, "role", None) == "Farmer":
                    # We need to check current group; we can't query directly, but we know we earlier set all farmers to "farm"
                    # So move from the pool by reassigning first 2*spawn_farmers_pairs farmers
                    if moved < 2 * spawn_farmers_pairs:
                        environment.assign_group(c, "spawn farmer")
                        moved += 1
                    else:
                        break

        # Update wheat consumption after potential farming spawns
        wheat_consumed = 10 * spawn_farmers_pairs
        wheat = max(0, wheat - wheat_consumed)

        # Note: We could spawn warriors too, but since Warriors must go to Cave, and haven't been
        # allocated to a "spawn warrior" group in this strategy, we skip that to preserve the rule.

        # Ensure Farmers remain in farm, except those moved to spawn
        # (No further action needed since we already assigned them appropriately)

        # No explicit return; changes are applied via environment.assign_group calls

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave (idle or waiting)
        - "village": Go to the Village (Farmers return to farming/spawning)
        """
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Farmers should go back to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave
                environment.assign_group(c, "cave")