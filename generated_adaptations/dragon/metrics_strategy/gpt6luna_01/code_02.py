from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned = {"spawn farmer": 0, "spawn warrior": 0}
        self.last_spawn_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors should move to the Cave as soon as they are in the Village.
        for villager in warriors:
            environment.assign_group(villager, "cave")

        wheat = environment.farm.wheat
        target = None

        # Pause after spawning so Farmers can return to farming and replenish wheat.
        can_spawn = self.last_spawn_step != step - 1 and len(farmers) >= 2

        if can_spawn:
            # Meet the minimum targets in a balanced order.
            if self.spawned["spawn warrior"] < 2:
                target = "spawn warrior"
            elif self.spawned["spawn farmer"] < 2:
                target = "spawn farmer"
            # Once both targets are met, use surplus Farmers and wheat to add Warriors.
            elif len(farmers) >= 4 and wheat >= 12:
                target = "spawn warrior"

            cost = {"spawn farmer": 10, "spawn warrior": 12}
            if target is not None and wheat >= cost[target]:
                pair = farmers[:2]
                for villager in pair:
                    environment.assign_group(villager, target)
                self.spawned[target] += 1
                self.last_spawn_step = step
                farmers = farmers[2:]
            else:
                target = None

        # Explicitly assign every remaining Farmer, including those not spawning.
        for villager in farmers:
            environment.assign_group(villager, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Keep all Warriors fighting, even when wounded, to maximize damage and
        # finish the Dragon as quickly as possible. Return Farmers to the Village.
        for villager in components:
            if villager.role == "Warrior":
                environment.assign_group(villager, "attack")
            else:
                environment.assign_group(villager, "village")