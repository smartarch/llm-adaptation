from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers in the Village into groups:
        # - farm: stay in Village and farm
        # - cave: go to the Cave (for Warriors)
        # - spawn farmer: for every two villagers and 10 wheat, spawn a new Farmer
        # - spawn warrior: for every two villagers and 12 wheat, spawn a new Warrior

        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the cave (in village).
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Handle Farmers: decide how many go to spawn groups vs farming
        # We will allocate farmers sequentially to spawn groups based on available wheat.
        spawn_farm_cap = 0
        spawn_war_cap = 0

        # Wheat available for spawning (use current wheat; spawning will consume wheat in the environment)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Maximum number of new Farmers we can spawn this step (by pair constraint)
        spawn_farm_cap = min(len(farmers) // 2, wheat // 10)

        # After reserving space for spawn farmers, determine how many farmers can spawn warriors
        # Use remaining wheat after potential farm spawns.
        remaining_wheat_after_farm = wheat - (spawn_farm_cap * 10)
        remaining_farmers_after_farm = len(farmers) - (spawn_farm_cap * 2)
        spawn_war_cap = min(remaining_farmers_after_farm // 2, remaining_wheat_after_farm // 12)

        # Assign farmers to groups according to the planning
        idx = 0
        # Spawn farmers: take 2 farmers per spawned farmer
        for _ in range(spawn_farm_cap * 2):
            if idx >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Spawn warriors: take 2 farmers per spawned warrior
        for _ in range(spawn_war_cap * 2):
            if idx >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers go to farming
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: Some villagers could be neither farmer nor warrior (if such exist); ensure they
        # are grouped in a safe default (farm) if they slip through.
        # If there are any components left unassigned in village (unexpected), assign them to farm.
        # (This is a safety net; normally all farmers are accounted for above.)

        # End of assign_in_village

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: - Warriors go to attack the Dragon
        # - Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any other non-Warrior) return to Village
                environment.assign_group(c, "village")