from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All warriors should go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among farmers
        remaining_farmers = list(farmers)  # copy

        to_spawn_farm = []  # two villagers -> spawn one new Farmer
        to_spawn_war = []   # two villagers -> spawn one new Warrior

        wheat = environment.farm.wheat if hasattr(environment, "farm") else 0

        # Try to spawn up to 2 farmers this step
        spawn_farm_slots = 2
        while len(remaining_farmers) >= 2 and wheat >= 10 and spawn_farm_slots > 0:
            a = remaining_farmers.pop(0)
            b = remaining_farmers.pop(0)
            to_spawn_farm.extend([a, b])
            wheat -= 10
            spawn_farm_slots -= 1

        # Try to spawn up to 2 warriors this step
        spawn_war_slots = 2
        while len(remaining_farmers) >= 2 and wheat >= 12 and spawn_war_slots > 0:
            a = remaining_farmers.pop(0)
            b = remaining_farmers.pop(0)
            to_spawn_war.extend([a, b])
            wheat -= 12
            spawn_war_slots -= 1

        # 3) Assign groups for spawning
        for c in to_spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_war:
            environment.assign_group(c, "spawn warrior")

        # 4) Remaining farmers stay in the village and farm
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")