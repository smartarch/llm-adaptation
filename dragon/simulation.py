import enum
from typing import TYPE_CHECKING

from base_classes.components import Component
from base_classes.simulation import Simulation, AssignmentError, ComponentAlreadyAssignedError
from utils import set_config_values

if TYPE_CHECKING:
    from dragon.components.villagers import Villager


VALID_IN_VILLAGE = ["farm", "cave", "spawn farmer", "spawn warrior"]
VALID_IN_CAVE = ["village", "cave", "attack"]


class DragonHuntSimulation(Simulation):

    def __init__(self, adapt: callable, config: dict):
        super().__init__(adapt, config)
        self.set_config_values(config)

        from dragon.components.villagers import Farmer, Warrior
        from dragon.components.dragon import Dragon

        self.dragon = Dragon(self)
        self.farm = Farm(self)
        self.components: list["Villager"] = \
            [Farmer(self) for _ in range(config["farmers"])] + \
            [Warrior(self) for _ in range(config["warriors"])]
        self.beyond_control_components = [self.dragon, self.farm]
        self.wheat = int(config["wheat"])

        self.spawn_farmer_ensemble = []
        self.spawn_warrior_ensemble = []

        self.last_components = self.components[:]  # for logging

    @staticmethod
    def set_config_values(config: dict):
        from dragon.components.villagers import Farmer, Warrior
        from dragon.components.dragon import Dragon
        set_config_values(config, "farmer", Farmer)
        set_config_values(config, "warrior", Warrior)
        set_config_values(config, "dragon", Dragon)

    def simulation_step(self, step):
        self.last_components = self.components[:]  # for logging
        super().simulation_step(step)

        # spawn new villagers
        from dragon.components.villagers import Warrior, Farmer
        if len(self.spawn_farmer_ensemble) >= 2:
            self._spawn_villager(self.spawn_farmer_ensemble, Farmer)
        if len(self.spawn_warrior_ensemble) >= 2:
            self._spawn_villager(self.spawn_warrior_ensemble, Warrior)
        self.spawn_farmer_ensemble = []
        self.spawn_warrior_ensemble = []

    def should_stop(self):
        return self.dragon.hp <= 0

    def should_adapt(self, step):
        return super().should_adapt(step) and len(self.components) > 0

    def get_villagers_in(self, location: "Map") -> list["Villager"]:
        from dragon.components.villagers import Villager
        return [villager for villager in self.components if isinstance(villager, Villager) and villager.location == location]

    def remove_component(self, component):
        self.components.remove(component)

    @property
    def dragon_hp(self):
        return self.dragon.hp

    def _spawn_villager(self, parents: list["Villager"], villager_type: type["Villager"]):
        count = len(parents) // 2
        for _ in range(count):
            if self.wheat < villager_type.SpawnCost:
                return

            self.wheat -= villager_type.SpawnCost
            self.components.append(villager_type(self))

    def get_globals(self):
        from dragon.components.villagers import Villager
        from dragon.components.dragon import Dragon

        return {
            "Map": Map,
            "Dragon": Dragon,
            "Villager": Villager,
            "Farm": Farm,
        }

    def _check_group(self, component: "Villager", group_id: str):
        if component in self.assignments:
            raise ComponentAlreadyAssignedError(component)

        if component.location == Map.VILLAGE:
            if group_id not in VALID_IN_VILLAGE:
                valid_groups = '"' + '", "'.join(VALID_IN_VILLAGE) + '"'
                raise AssignmentError(f'Invalid group for Villager in Village: "{group_id}". It must be one of {valid_groups}.')
        else:  # component.location == Map.CAVE
            if group_id not in VALID_IN_CAVE:
                valid_groups = '"' + '", "'.join(VALID_IN_CAVE) + '"'
                raise AssignmentError(f'Invalid group for Villager in Cave: "{group_id}". It must be one of {valid_groups}.')

    def _assign_group(self, component: "Villager", group_id: str):
        from dragon.components.villagers import VillagerState

        if component.location == Map.VILLAGE:
            match group_id.strip():
                case "farm":
                    component.state = VillagerState.FARMING
                case "cave":
                    component.state = VillagerState.MOVING_TO_CAVE
                case "spawn farmer":
                    component.state = VillagerState.SPAWNING
                    self.spawn_farmer_ensemble.append(component)
                case "spawn warrior":
                    component.state = VillagerState.SPAWNING
                    self.spawn_warrior_ensemble.append(component)
        else:  # component.location == Map.CAVE
            match group_id.strip():
                case "village":
                    component.state = VillagerState.MOVING_TO_VILLAGE
                case "cave":
                    component.state = VillagerState.IDLE
                case "attack":
                    component.state = VillagerState.ATTACKING


class Map(enum.Enum):
    VILLAGE = enum.auto()
    CAVE = enum.auto()


class Farm(Component):

    simulation: DragonHuntSimulation

    @property
    def wheat(self):
        return self.simulation.wheat
