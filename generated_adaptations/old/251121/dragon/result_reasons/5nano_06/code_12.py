from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In the Village:
        # - Farmers stay in Village (farm)
        # - Warriors head to the Cave (cave) to attack
        # - Spawn farmers/warriors conservatively when wheat allows
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 1) Spawn farmer: need at least 4 farmers and wheat >= 10
        to_spawn_farm = []
        if len(farmers) >= 4 and wheat >= 10:
            to_spawn_farm = farmers[:2]  # two farmers join spawn farmer group
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")

        # Remaining farmers (not spawning) go to farming
        for c in farmers:
            if c in to_spawn_farm:
                continue
            environment.assign_group(c, "farm")

        # 2) Spawn warrior: require sufficient total warriors and wheat >= 12
        remaining_warriors = [w for w in warriors if w not in to_spawn_farm]
        to_spawn_war = []
        if len(remaining_warriors) >= 4 and wheat >= 12:
            # Use two warriors to seed a new Warrior
            to_spawn_war = remaining_warriors[:2]
            for c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")

        # Remaining warriors (not spawning) head to the Cave
        for c in remaining_warriors:
            if c not in to_spawn_war:
                environment.assign_group(c, "cave")

        # End of village assignment. In subsequent steps, assign_in_cave will handle moving to attack.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")