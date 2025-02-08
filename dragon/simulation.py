import enum
from typing import TYPE_CHECKING

from base_classes.simulation import Simulation
from utils import set_config_values

if TYPE_CHECKING:
    from dragon.components.villagers import Villager


class DragonHuntSimulation(Simulation):

    def __init__(self, adapt: callable, config: dict):
        super().__init__(adapt, config)
        self.set_config_values(config)

        from dragon.components.villagers import Farmer, Warrior
        from dragon.components.dragon import Dragon

        self.dragon = Dragon(self)
        self.components = \
            [Farmer(self) for _ in range(config["farmers"])] + \
            [Warrior(self) for _ in range(config["warriors"])] + \
            [self.dragon]
        self.wheat = int(config["wheat"])

    @staticmethod
    def set_config_values(config: dict):
        from dragon.components.villagers import Farmer, Warrior
        from dragon.components.dragon import Dragon
        set_config_values(config, "farmer", Farmer)
        set_config_values(config, "warrior", Warrior)
        set_config_values(config, "dragon", Dragon)

    def get_villagers_in(self, location: "Map") -> list["Villager"]:
        from dragon.components.villagers import Villager
        return [villager for villager in self.components if isinstance(villager, Villager) and villager.location == location]

    def remove_component(self, component):
        self.components.remove(component)

    @property
    def dragon_hp(self):
        return self.dragon.hp

    def spawn_farmer(self, parents: list["Villager"]):
        # TODO: this should be an ensemble and we should check that parents are idle
        from dragon.components.villagers import Farmer, VillagerState
        if len(parents) < 2:
            return
        self.wheat -= Farmer.SpawnCost
        self.components.append(Farmer(self))
        for parent in parents:
            parent.state = VillagerState.IDLE

    def spawn_warrior(self, parents: list["Villager"]):
        # TODO: this should be an ensemble and we should check that parents are idle
        from dragon.components.villagers import Warrior, VillagerState
        if len(parents) < 2:
            return
        self.wheat -= Warrior.SpawnCost
        self.components.append(Warrior(self))
        for parent in parents:
            parent.state = VillagerState.IDLE


class Map(enum.Enum):
    VILLAGE = enum.auto()
    CAVE = enum.auto()
