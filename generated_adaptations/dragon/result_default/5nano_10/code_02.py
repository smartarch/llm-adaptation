from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        num_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawns we can attempt to do this step
        # Spawn Farmer: 2 villagers in spawn_farm group and 10 wheat -> 1 new Farmer
        # Spawn Warrior: 2 villagers in spawn_warrior group and 12 wheat -> 1 new Warrior
        spawn_farm_pairs = min(wheat // 10, num_farmers // 2)
        spawn_farm_count = 2 * spawn_farm_pairs

        remaining_wheat_after_farm_spawns = wheat - spawn_farm_pairs * 10
        remaining_farmers_after_farm_spawns = num_farmers - spawn_farm_count

        spawn_warrior_pairs = min(remaining_wheat_after_farm_spawns // 12, remaining_farmers_after_farm_spawns // 2)
        spawn_warrior_count = 2 * spawn_warrior_pairs

        # Assign farmers to their respective groups
        # First 2*spawn_farm_pairs to "spawn farmer"
        # Next 2*spawn_warrior_pairs to "spawn warrior"
        # The rest to "farm"
        idx = 0
        for f in farmers:
            if idx < spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
            elif idx < spawn_farm_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")
            idx += 1

        # Assign all Warriors to cave (to go to the cave)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack the Dragon.
        # Farmers should move back to the Village.
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role (shouldn't happen)
                environment.assign_group(c, "cave")