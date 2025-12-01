import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the Cave (prepare for attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) All Farmers should stay in the Village by default (farm)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Spawn logic (spawn a few new villagers if resources allow)
        # Current wheat in the farm
        current_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We'll try to spawn at most two villagers per update to stay conservative
        # First, attempt to spawn a Farmer (needs 2 villagers in "spawn farmer" and >= 10 wheat)
        if len(farmers) >= 2 and current_wheat >= 10:
            to_spawn_farmers = farmers[:2]  # take first two farmers to spawn
            for c in to_spawn_farmers:
                environment.assign_group(c, "spawn farmer")
            # After triggering a farmer spawn, wheat will be consumed by the environment;
            # attempt to spawn a Warrior if resources allow and we have more farmers left
            # Check remaining farmers (excluding those just assigned to spawn farmer)
            remaining_after_farm_spawn = farmers[2:]
            if len(remaining_after_farm_spawn) >= 2 and current_wheat >= 12:
                to_spawn_warriors = remaining_after_farm_spawn[:2]
                for c in to_spawn_warriors:
                    environment.assign_group(c, "spawn warrior")
        else:
            # If not enough to spawn a farmer, try spawning a Warrior directly if resources allow
            if len(farmers) >= 2 and current_wheat >= 12:
                to_spawn_warriors = farmers[:2]
                for c in to_spawn_warriors:
                    environment.assign_group(c, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep them in cave if role is unknown
                environment.assign_group(c, "cave")