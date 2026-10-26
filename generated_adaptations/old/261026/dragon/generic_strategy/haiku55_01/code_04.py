from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Aggressive damage strategy:
    - Warriors always go to the Cave.
    - Farmers join the attack in the Cave (1 damage each) instead of going home,
      while a few keep farming and some are used to spawn extra Warriors.
    - Warrior spawning has priority over farmer spawning.
    - Only villagers at 1 HP or less retreat from the Cave.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_batches = 0
        self.farmer_spawn_batches = 0
        self.max_warrior_batches = 4
        self.max_farmer_batches = 2
        self.retreat_hp = 1  # villagers with hp <= this retreat from the Cave

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior goes to the Cave to attack the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Priority 1: spawn Warriors (3 damage each) while wheat allows.
        wheat_left = wheat
        while (self.warrior_spawn_batches < self.max_warrior_batches
               and wheat_left >= 12 and len(available) >= 2):
            spawn_warrior_group = available[:2]
            available = available[2:]
            self.warrior_spawn_batches += 1
            wheat_left -= 12
            break  # one batch per step; spawning is slow, so keep the rest farming

        # Priority 2: spawn Farmers only if plenty of wheat remains and
        # enough farmers are left to keep the farm running.
        if (self.farmer_spawn_batches < self.max_farmer_batches
                and wheat_left >= 10 and len(available) >= 4):
            spawn_farmer_group = available[:2]
            available = available[2:]
            self.farmer_spawn_batches += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers: keep farming so wheat keeps coming in,
        # unless the Dragon is nearly dead, in which case everyone attacks.
        dragon_hp = environment.dragon.hp
        for f in available:
            if dragon_hp <= 15:
                environment.assign_group(f, "cave")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.hp <= self.retreat_hp:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")