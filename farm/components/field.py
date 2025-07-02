from typing import TYPE_CHECKING

import numpy as np

from base_classes.components import Component
from base_classes.components2d import Point2D

if TYPE_CHECKING:
    from farm.components.drone import Drone
    from farm.simulation import SmartFarmSimulation


class Field(Component):
    """
    A rectangular Field on the farm.

    (left,top) .__________
               |          |
               |__________|.(right,bottom)
    """

    # type hint
    simulation: "SmartFarmSimulation"

    def __init__(self, simulation, top, left, bottom, right):
        """
        Initiate the field with one crop per grid point.
        """
        super().__init__(simulation)

        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right

        self.crops = np.ones((right - left + 1, bottom - top + 1))  # rectangle of crops
        self.damage = 0  # total damage
        self.damagedThisStep = set()

        from farm.components.drone import Drone
        self.protectingDrones: set[Drone] = set()
        self.arrivingDrones: set[Drone] = set()
        self.patrollingPlaces = self.computePatrollingPlaces(Drone.Radius - 2)
        self.protectionPlaces: dict[Point2D, list[Drone]] = \
            {place: [] for place in self.computeProtectionPlaces(Drone.Radius - 2)}

        self.birds = []

    def patrollingProtection(self) -> bool:
        return self.simulation.config.get("patrolling", False)

    def computePatrollingPlaces(self, radius):
        patrolLeft = self.left + radius
        patrolTop = self.top + radius
        patrolRight = self.right - radius + 1
        patrolBottom = self.bottom - radius + 1

        return [
            Point2D(patrolLeft, patrolTop),
            Point2D((patrolLeft + patrolRight) / 2, patrolTop),
            Point2D(patrolRight, patrolTop),
            Point2D(patrolRight, (patrolTop + patrolBottom) / 2),
            Point2D(patrolRight, patrolBottom),
            Point2D((patrolLeft + patrolRight) / 2, patrolBottom),
            Point2D(patrolLeft, patrolBottom),
            Point2D(patrolLeft, (patrolTop + patrolBottom) / 2),
        ]

    def computeProtectionPlaces(self, radius):
        return [Point2D(x, y)
                for x in range(self.left + radius, self.right + 1, radius * 2)
                for y in range(self.top + radius, self.bottom + 1, radius * 2)]

    def isPointInField(self, point):
        """
        Checks if the given point is inside the field.
        """
        return self.left <= point.x <= self.right and \
            self.top <= point.y <= self.bottom

    def findClosestUnprotectedPlace(self, drone: "Drone") -> Point2D:
        if self.patrollingProtection():
            places = self.patrollingPlaces
        else:
            # find the place that needs protection (unprotected or with the least number of drones)
            leastDrones = len(min(self.protectionPlaces.values(), key=len))
            if leastDrones != 0:
                print(f"{drone.id} assigned to a fully protected {self.id}")
            places = [p for p in self.protectionPlaces if len(self.protectionPlaces[p]) == leastDrones]

        return min(places, key=lambda p: p.distance(drone.location))

    def closestPlaceToDrone(self, drone: "Drone") -> Point2D:
        return min(self.protectionPlaces, key=lambda p: p.distance(drone.location))

    def assignNextPlace(self, drone: "Drone") -> Point2D:
        if self.patrollingProtection():
            try:
                return self.assignNextPatrollingPlace(drone)
            except ValueError:
                return self.findClosestUnprotectedPlace(drone)
        else:
            # primary protecting drones (first in the list) stay at the same place
            for place in self.protectionPlaces:
                if len(self.protectionPlaces[place]) > 0 and self.protectionPlaces[place][0] == drone:
                    return place
            # remove drone from all other places
            for place in self.protectionPlaces:
                if drone in self.protectionPlaces[place]:
                    self.protectionPlaces[place].remove(drone)
            # find the closest and least protected place
            place = self.findClosestUnprotectedPlace(drone)
            self.protectionPlaces[place].append(drone)
            return place

    def unassignDrone(self, drone: "Drone"):
        # remove drone from all places
        for place in self.protectionPlaces:
            if drone in self.protectionPlaces[place]:
                self.protectionPlaces[place].remove(drone)

    def assignNextPatrollingPlace(self, drone: "Drone"):
        currentPlaceIndex = self.patrollingPlaces.index(drone.location)
        newPlaceIndex = (currentPlaceIndex + 1) % len(self.patrollingPlaces)
        return self.patrollingPlaces[newPlaceIndex]

    def eatCrop(self, point):
        """Damages the crop at the given point. Returns false if the crop is already damaged."""
        if not self.isPointInField(point):
            raise ValueError(f"Point {point} is not in the field!")

        if self.crops[point.x - self.left, point.y - self.top] > 0:
            self.crops[point.x - self.left, point.y - self.top] -= 1
            self.damage += 1
            self.damagedThisStep.add(point)
            return True

        return False

    def randomUndamagedCrop(self):
        """
        Finds a random undamaged crop position. Returns None if field is empty.
        """
        undamaged = self.crops > 0
        coordinates = np.argwhere(undamaged)
        return self.__randomCrop(coordinates)

    def randomUnprotectedCrop(self):
        undamaged = self.crops > 0
        coordinates = np.argwhere(undamaged)

        if len(coordinates) == 0:
            return None

        def point_unprotected(point):
            for drone in self.simulation.drones:
                if drone.protectsPoint(Point2D(point)):
                    return False
            return True

        # try 20 random points and see if there is an unprotected one
        for _ in range(20):
            idx = np.random.choice(len(coordinates))
            x, y = coordinates[idx]
            point = Point2D(x + self.left, y + self.top)

            if point_unprotected(point):
                return point

        print("Could not find unprotected crop")
        return None
        # Slow version: try all points
        # unprotected = list(filter(point_unprotected, coordinates))
        # return self.__randomCrop(unprotected)

    def __randomCrop(self, cropCoordinates):

        if len(cropCoordinates) == 0:
            return None
        # select random
        idx = np.random.choice(len(cropCoordinates))
        x, y = cropCoordinates[idx]
        return Point2D(x + self.left, y + self.top)

    @property
    def threat_level(self):
        if len(self.birds) == 0:
            return 0

        birds_inside = len([
            bird for bird in self.birds
            if bird.location.is_inside(self.left, self.top, self.right, self.bottom)
        ])
        return birds_inside / len(self.birds)

    @property
    def drones_for_full_protection(self) -> int:
        """Total number of drones necessary for full protection."""
        return len(self.protectionPlaces)

    @property
    def remaining_drones_for_full_protection(self) -> int:
        return len(self.protectionPlaces) - len(self.protectingDrones)

    @property
    def protecting_drones(self):
        return len(self.protectingDrones)

    @property
    def arriving_drones(self):
        return len(self.arrivingDrones)

    @property
    def isFullyProtected(self):
        return len(self.protectionPlaces) == len(self.protectingDrones)

    def __str__(self):
        return self.id

    def __repr__(self):
        return f"{self.id}({self.top},{self.left},{self.bottom},{self.right})"
