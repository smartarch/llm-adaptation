import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split current villagers in village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: Farmers stay in farm, Warriors go to cave
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Spawn logic:
        # Try to spawn 1st Farmer if possible (needs 2 villagers in spawn farmer and 10 wheat)
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            # Take first two Farmers to spawn Farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Remaining Farmers (if any) stay farming; Warriors already moved to cave above
            # No further action needed here; the engine will spawn if wheat consumed
        # Try to spawn Warrior if possible (needs 2 villagers in spawn warrior and 12 wheat)
        # Only if we have enough farmers left after potential spawn farmer designation
        remaining_farmers = farmers[2:] if len(farmers) >= 2 else []
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for c in remaining_farmers[:2]:
                environment.assign_group(c, "spawn warrior")
        # If not enough farmers for the above, ensure there are enough villagers in spawning groups by fallback
        # Do not assign anyone else to spawn groups; keep existing assignments for other villagers

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In cave: send Warriors to attack Dragon; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # If unknown role, default to staying in cave (safe fallback)
                environment.assign_group(c, "cave")