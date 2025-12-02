from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in the Village into farming, cave-bound warriors, and spawn groups.
        # Farmers stay in Village (farm) or spawn more villagers (spawn farmer).
        # Warriors move to Cave (cave) to eventually attack Dragon, and may spawn more warriors (spawn warrior).

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available (best effort; farm object may be absent in some test environments)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # How many spawns are possible this step
        max_farm_spawns = 0
        if len(farmers) >= 2:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        max_war_spawns = 0
        if len(warriors) >= 2:
            max_war_spawns = min(len(warriors) // 2, wheat // 12)

        # We'll spawn up to 2 of each type if possible
        farm_spawn = min(2, max_farm_spawns)
        war_spawn = min(2, max_war_spawns)

        # Allocate farmers for spawning
        spawn_farm = farmers[:farm_spawn * 2]
        # Remaining farmers stay in farm
        for c in farmers[farm_spawn * 2:]:
            environment.assign_group(c, "farm")

        # Allocate warriors for spawning
        spawn_war = warriors[:war_spawn * 2]
        # Remaining warriors go to cave (to eventually attack)
        for c in warriors[war_spawn * 2:]:
            environment.assign_group(c, "cave")

        # Assign spawn groups for spawning (they will generate new villagers)
        for c in spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_war:
            environment.assign_group(c, "spawn warrior")

        # If there are any villagers not yet assigned (edge cases), ensure they get assigned.
        # In this setup, all villagers are accounted for above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, every Warrior should attack the Dragon; Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")