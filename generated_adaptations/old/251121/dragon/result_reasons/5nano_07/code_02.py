from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Decide on spawn groups (stay in the Village but trigger spawns)
        spawn_farmers = []
        spawn_warriors = []

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn up to 2 Farmers if there are enough Farmers and wheat
        if step <= 15 and len(farmers) >= 4 and wheat >= 10:
            spawn_farmers = farmers[:2]

        # Attempt to spawn Warriors using remaining Farmers if there is enough wheat
        remaining_for_warrior = [f for f in farmers if f not in spawn_farmers]
        if step <= 15 and len(remaining_for_warrior) >= 2 and wheat >= 12:
            spawn_warriors = remaining_for_warrior[:2]

        spawn_farm_set = set(spawn_farmers)
        spawn_war_set = set(spawn_warriors)

        # Assign groups for Farmers
        for f in farmers:
            if f in spawn_farm_set:
                environment.assign_group(f, "spawn farmer")
            elif f in spawn_war_set:
                environment.assign_group(f, "spawn warrior")
            else:
                # Default: stay in Village and farm
                environment.assign_group(f, "farm")

        # Assign groups for Warriors: move to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")