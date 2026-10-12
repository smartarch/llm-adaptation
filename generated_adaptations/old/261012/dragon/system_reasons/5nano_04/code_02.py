from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_state = {}

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups:
        # - "farm": stay in Village and farm
        # - "cave": go to the Cave
        # - "spawn farmer": spawn new Farmer (needs 2 villagers + 10 wheat)
        # - "spawn warrior": spawn new Warrior (needs 2 villagers + 12 wheat)

        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers stay in farm
        for f in farmers:
            environment.assign_group(f, "farm")

        # Wheat available on the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine farmers to assign to spawn groups
        to_spawn_farmers = []
        if len(farmers) >= 2 and wheat >= 10:
            to_spawn_farmers = farmers[:2]
            for c in to_spawn_farmers:
                environment.assign_group(c, "spawn farmer")

        # Remaining farmers after selecting spawn farmers
        remaining_after_farm_spawn = [f for f in farmers if f not in to_spawn_farmers]

        to_spawn_warriors = []
        if len(remaining_after_farm_spawn) >= 2 and wheat >= 12:
            to_spawn_warriors = remaining_after_farm_spawn[:2]
            for c in to_spawn_warriors:
                environment.assign_group(c, "spawn warrior")

        # Any farmers not involved in spawning stay farming
        # (They were already assigned to "farm" above; nothing else to do)

        # Move all Warriors toward the Cave (preparation for attack next step)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors attack the Dragon
        # - Farmers go back to Village (stay in Village)
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")