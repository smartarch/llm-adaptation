from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy (improved, aggressive spawning):
        - All Warriors should stay in the Cave to attack; move them now.
        - Farmers stay in the Village and can either farm or spawn new villagers.
        - Spawn as many Farmers as possible this step (2 per spawn, cost 10 wheat per spawn).
        - With any remaining Farmers and Wheat, spawn as many Warriors as possible (2 per spawn, cost 12 wheat per spawn).
        - This maximizes early DPS growth while ensuring ongoing population expansion.
        - The spawned villagers (both Farmer and Warrior) will appear in the Village; they will move to the Cave in the next step if needed.
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Always send Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available at the Farm
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Max possible farmer spawns this step: 2 farmers per spawn, 10 wheat per spawn
        farm_spawns = 0
        if len(farmers) >= 2 and wheat >= 10:
            farm_spawns = min(len(farmers) // 2, wheat // 10)

        wheat_after_farm = wheat - farm_spawns * 10
        remaining_farmers = len(farmers) - 2 * farm_spawns

        # Max possible warrior spawns this step: 2 warriors per spawn, 12 wheat per spawn
        war_spawns = 0
        if remaining_farmers >= 2 and wheat_after_farm >= 12:
            war_spawns = min(remaining_farmers // 2, wheat_after_farm // 12)

        spawn_farmer_count = 2 * farm_spawns
        spawn_warrior_count = 2 * war_spawns

        # Assign farmers to appropriate groups
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy in the Cave:
        - All Warriors attack the Dragon.
        - Farmers should stay in the Village (not in cave to be attacked by Dragon).
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")