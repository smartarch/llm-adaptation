from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors are sent to the Cave and attack the Dragon.
    Farmers stay in the Village, farm wheat, and are used to spawn
    new farmers and warriors whenever enough wheat is available.
    """

    FARMER_SPAWN_WHEAT = 10
    WARRIOR_SPAWN_WHEAT = 12
    SPAWN_GROUP_SIZE = 2

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the Cave to attack the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide at most one spawn per step, using farmers only.
        # Remaining farmers keep farming.
        spawn_warrior_ids = set()
        spawn_farmer_ids = set()
        n = self.SPAWN_GROUP_SIZE

        if len(farmers) >= n and wheat >= self.WARRIOR_SPAWN_WHEAT:
            # Prefer spawning warriors: they deal the most damage.
            for f in farmers[:n]:
                spawn_warrior_ids.add(id(f))
        elif len(farmers) >= n and wheat >= self.FARMER_SPAWN_WHEAT:
            # Otherwise grow the farmer population.
            for f in farmers[:n]:
                spawn_farmer_ids.add(id(f))

        for f in farmers:
            if id(f) in spawn_warrior_ids:
                environment.assign_group(f, "spawn warrior")
            elif id(f) in spawn_farmer_ids:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in the Cave; send them home.
                environment.assign_group(c, "village")