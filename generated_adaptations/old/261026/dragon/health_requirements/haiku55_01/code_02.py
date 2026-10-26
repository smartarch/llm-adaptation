from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors always go to the Cave and attack the Dragon.
    - Farmers stay in the Village on the farm by default.
    - Wheat is spent to spawn warriors first (more damage), then farmers
      (economy) during the early game.
    - Any farmer found in the Cave is sent back to the Village.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    EARLY_GAME_STEPS = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to the cave to fight the dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Default: farmers work the farm.
        available_farmers = list(farmers)
        assigned_farmers = set()

        # Spawn warriors first (stronger attackers), needs 2 villagers + 12 wheat.
        if wheat >= self.WARRIOR_SPAWN_COST and len(available_farmers) >= 2:
            for f in available_farmers[:2]:
                environment.assign_group(f, "spawn warrior")
                assigned_farmers.add(id(f))
            wheat -= self.WARRIOR_SPAWN_COST
            available_farmers = [f for f in available_farmers if id(f) not in assigned_farmers]

        # Spawn farmers during the early game to grow the economy.
        if (step <= self.EARLY_GAME_STEPS
                and wheat >= self.FARMER_SPAWN_COST
                and len(available_farmers) >= 2):
            for f in available_farmers[:2]:
                environment.assign_group(f, "spawn farmer")
                assigned_farmers.add(id(f))
            wheat -= self.FARMER_SPAWN_COST
            available_farmers = [f for f in available_farmers if id(f) not in assigned_farmers]

        # Remaining farmers stay on the farm.
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking the dragon.
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers do not fight; send them back to the village.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")