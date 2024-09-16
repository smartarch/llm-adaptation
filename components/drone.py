from enum import Enum

from base_classes.components2d import MovingComponent2D, Point2D


class DroneState(Enum):
    IDLE = 0
    CHARGING = 1
    # TODO


class Drone(MovingComponent2D):

    DroneSpeed = 1
    DroneRadius = 5

    def __init__(self, simulation, location):
        super().__init__(simulation, location, Drone.DroneSpeed)
        self.battery = 1
        self.state = DroneState.IDLE

    def protectsPoint(self, point: Point2D) -> bool:
        """Returns true if the point is protected by this drone."""
        return self.location.distance(point) <= Drone.DroneRadius

    def __repr__(self):
        return f"{self.id}({str(self.state)}, bat={self.battery:.3f})"
