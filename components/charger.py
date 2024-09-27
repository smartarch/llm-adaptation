from typing import TYPE_CHECKING

from base_classes.components2d import StationaryComponent2D, Point2D

if TYPE_CHECKING:
    from components.drone import Drone


class Charger(StationaryComponent2D):

    ChargingRate = 0.01

    def __init__(self, simulation, location: Point2D):
        super().__init__(simulation, location)

        self.chargingDrones: set["Drone"] = set()

    def actuate(self):
        done_charging = []
        for drone in self.chargingDrones:
            drone.battery += Charger.ChargingRate
            if drone.battery >= 1:
                done_charging.append(drone)

        for drone in done_charging:
            drone.assignTarget(None)  # stop charging

    def __repr__(self):
        return f"{self.id}"
