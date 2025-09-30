import random

from base_classes.components2d import Point2D
from base_classes.simulation import Simulation, AssignmentError, ComponentAlreadyAssignedError, InvalidGroupError
from farm.components.bird import Bird, BirdFieldProbabilityGenerator
from farm.components.charger import Charger
from farm.components.drone import Drone, DroneState
from farm.components.field import Field


class SmartFarmSimulation(Simulation):

    def __init__(self, adapt: callable, config: dict):
        super().__init__(adapt, config)

        self.mapWidth = config["mapWidth"]
        self.mapHeight = config["mapHeight"]

        self.fields: list[Field] = [Field(self, *coords) for coords in config["fields"]]
        self.autoChargeDrones = config.get("autoCharging", False)
        self.drones: list[Drone] = [Drone(self, self.randomPoint(), self.autoChargeDrones) for _ in range(config["drones"])]
        self.dronesDict = {drone.id: drone for drone in self.drones}
        self.birds: list[Bird] = [Bird(self, self.randomPoint()) for _ in range(config["birds"])]
        self.charger = Charger(self, config["charger"])

        self.fieldProbabilityGenerator = BirdFieldProbabilityGenerator(self, config["birdFieldProbabilities"], config["birdCohesion"])

        self.components = self.drones
        self.beyond_control_components = self.fields + [self.charger]

        self.set_config_values(config)

    @staticmethod
    def set_config_values(config: dict):
        if "drone" in config:
            for key in config["drone"]:
                if key in Drone.__dict__:
                    setattr(Drone, key, config["drone"][key])
                else:
                    raise KeyError(f"Unknown drone attribute: {key}")
        if "bird" in config:
            for key in config["bird"]:
                if key in Bird.__dict__:
                    setattr(Bird, key, config["bird"][key])
                else:
                    raise KeyError(f"Unknown bird attribute: {key}")

    def actuate_components(self):
        # override to get custom actuation order
        for component in [self.fieldProbabilityGenerator] + self.fields + self.drones + self.birds + [self.charger]:
            component.actuate()

    @property
    def total_damage(self):
        return sum(field.damage for field in self.fields)

    def randomPoint(self):
        return Point2D.random(0, 0, self.mapWidth, self.mapHeight)

    def notTerminatedDrones(self):
        return filter(lambda d: d.state != DroneState.TERMINATED, self.drones)

    def availableDrones(self):
        if self.autoChargeDrones:
            return filter(lambda d: d.state not in (DroneState.TERMINATED, DroneState.MOVING_TO_CHARGER, DroneState.CHARGING), self.drones)
        else:
            return self.notTerminatedDrones()

    def terminatedDrones(self):
        return filter(lambda d: d.state == DroneState.TERMINATED, self.drones)

    def _check_group(self, drone: Drone, group_id: str):
        if drone in self.assignments:
            raise ComponentAlreadyAssignedError(drone)
        if group_id.strip() == "idle":
            return
        elif group_id.strip().startswith("protecting"):
            try:
                self._parse_field(group_id)
            except (KeyError, IndexError):
                raise AssignmentError(f"Invalid field in protecting group: {group_id}")
        else:
            raise InvalidGroupError(group_id)

    def _parse_field(self, group_id):
        field_id = group_id.strip().split()[1]
        for field in self.fields:
            if field.id == field_id:
                return field
        raise KeyError

    def _assign_group(self, drone: Drone, group_id: str):
        if group_id.strip() == "idle":
            drone.assignTarget(None)
        elif group_id.strip().startswith("protecting"):
            drone.assignTarget(self._parse_field(group_id))

    def get_globals(self):
        return super().get_globals() | {
            "DroneState": DroneState,
            "Field": Field,
            "Drone": Drone,
        }

    def random_assign_and_simulate(self, protecting_count, steps):
        drones = self.drones[:protecting_count]
        self.random_assign_drones(drones)

        should_adapt = self.should_adapt
        self.should_adapt = lambda _step: False
        self.run_simulation(steps)
        self.should_adapt = should_adapt

    def random_assign_drones(self, drones=None):
        if drones is None:
            drones = self.availableDrones()
        for drone in drones:
            fields = [f for f in self.fields if f.threat_level > 0 and not f.isFullyAssigned]
            drone.assignTarget(random.choice(fields))
