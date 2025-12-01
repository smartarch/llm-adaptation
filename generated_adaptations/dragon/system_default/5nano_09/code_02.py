from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Organize villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave (they will attack in the cave phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning logic for Farmers (spawn events use two villagers + wheat)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        spawn_warrior_pair = []
        spawn_farmer_pair = []
        # Prefer spawning a Warrior if we have enough wheat and at least 2 Farmers available
        if len(farmers) >= 2 and wheat >= 12:
            spawn_warrior_pair = farmers[:2]
        # If Warrior spawn isn't triggered, try to spawn a Farmer
        elif len(farmers) >= 2 and wheat >= 10:
            spawn_farmer_pair = farmers[:2]

        assigned_spawn = set(spawn_warrior_pair) | set(spawn_farmer_pair)

        # Assign groups for Farmers
        for f in farmers:
            if f in spawn_warrior_pair:
                environment.assign_group(f, "spawn warrior")
            elif f in spawn_farmer_pair:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack the Dragon; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any other non-warrior types) go to Village
                environment.assign_group(c, "village")