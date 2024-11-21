from enum import Enum
from typing import Optional

from base_classes.components2d import MovingComponent2D, Point2D
from components.charger import Charger
from components.field import Field


class DroneState(Enum):
    IDLE = 0
    CHARGING = 1
    PROTECTING = 2
    MOVING_TO_CHARGER = 3
    MOVING_TO_FIELD = 4
    TERMINATED = 5

    def __str__(self):
        return self.name


class Drone(MovingComponent2D):

    Speed = 2
    Radius = 6
    MovingEnergyConsumption = 0.01
    HoveringEnergyConsumption = 0.007
    IdleEnergyConsumption = 0

    def __init__(self, simulation, location):
        super().__init__(simulation, location, Drone.Speed)
        self.battery = 1
        self.state = DroneState.IDLE
        self.target: Optional[Field | Charger] = None
        self.targetLocation = None

    def actuate(self):
        if self.state == DroneState.TERMINATED:  # no action
            return

        # fly towards assigned target
        if self.targetLocation is not None:
            self.flyTowardsTarget()

        if self.state == DroneState.IDLE:
            self.consumeBattery(Drone.IdleEnergyConsumption)

        self.checkBattery()

    def assignTarget(self, target: Optional[Field | Charger]):
        if self.target == target:
            print(f"Assigning same target to {self}: {target}")
            return

        print(f"Assigning new target to {self}: {target}")
        self.unassignPreviousTarget()
        self.target = target
        if target is not None:
            if isinstance(self.target, Charger):
                self.targetLocation = target.location
                self.state = DroneState.MOVING_TO_CHARGER
            elif isinstance(self.target, Field):
                self.state = DroneState.MOVING_TO_FIELD
                self.targetLocation = target.assignNextPlace(self)
        else:
            self.targetLocation = None
            self.state = DroneState.IDLE

    def unassignPreviousTarget(self):
        if self.target is None:
            return
        if isinstance(self.target, Field):
            self.target.protectingDrones.discard(self)
            self.target.unassignDrone(self)
        if isinstance(self.target, Charger):
            self.target.chargingDrones.discard(self)

    def checkBattery(self):
        if self.battery <= 0:
            self.battery = 0
            self.state = DroneState.TERMINATED
            self.unassignPreviousTarget()

    def flyTowardsTarget(self):
        if self.move(self.targetLocation):
            self.targetReached()

    def targetReached(self):
        self.targetLocation = None
        if isinstance(self.target, Charger):
            self.startCharging()
        elif isinstance(self.target, Field):
            self.startProtecting()

    def startProtecting(self):
        self.targetLocation = self.target.assignNextPlace(self)
        self.target.protectingDrones.add(self)
        self.state = DroneState.PROTECTING

    def startCharging(self):
        self.target.chargingDrones.add(self)
        self.state = DroneState.CHARGING

    def move(self, target=None):
        """It moves the drone by using the MovingComponent2D.move method, with addition of decreasing the battery in moving consumption rate."""
        if not self.simulation.config.get("patrolling", False) and self.state == DroneState.PROTECTING:
            self.consumeBattery(Drone.HoveringEnergyConsumption)
        else:
            self.adjustSpeed()
            self.consumeBattery(Drone.MovingEnergyConsumption)
        return super().move(self.targetLocation)

    def adjustSpeed(self):
        """Slow down if another drone is in front of this one when patrolling."""
        self.speed = Drone.Speed
        if self.state != DroneState.PROTECTING:
            return

        for drone in self.target.protectingDrones:
            if drone == self:
                continue
            if self.location.distance(drone.location) < Drone.Radius * 1.5:  # nearby drone
                myTargetDirection = self.targetLocation - self.location
                droneDirection = drone.location - self.location
                dotProductToDrone = myTargetDirection[0] * droneDirection[0] + myTargetDirection[1] * droneDirection[1]
                if dotProductToDrone > 0:  # other drone is in front of this one
                    droneTargetDirection = drone.targetLocation - self.location
                    dotProductTargets = myTargetDirection[0] * droneTargetDirection[0] + myTargetDirection[1] * droneTargetDirection[1]
                    if dotProductTargets >= 0:  # drones are headed in similar directions (not opposite each other)
                        # slow down
                        self.speed = Drone.Speed * 0.5
                        return

    def consumeBattery(self, batteryConsumptionRate):
        self.battery -= batteryConsumptionRate

    def protectsPoint(self, point: Point2D) -> bool:
        """Returns true if the point is protected by this drone."""
        if self.state in (DroneState.IDLE, DroneState.TERMINATED):
            return False
        return self.location.distance(point) <= Drone.Radius

    def protectRadiusBox(self) -> tuple[float, float, float, float]:
        """Gives the radius of the drone as form of rectangle to be presented in visualization."""
        startX = self.location.x - Drone.Radius
        endX = self.location.x + Drone.Radius
        startY = self.location.y - Drone.Radius
        endY = self.location.y + Drone.Radius
        startX = max(startX, 0)
        startY = max(startY, 0)
        return startX, startY, endX, endY

    def __repr__(self):
        return f"{self.id}({str(self.state)}, bat={self.battery:.3f})"

    def energyToFlyToCharger(self) -> float:
        distance = self.location.distance(self.simulation.charger.location)
        time = distance / self.speed
        return Drone.MovingEnergyConsumption * time
