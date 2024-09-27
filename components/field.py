import random
from typing import TYPE_CHECKING

import numpy as np

from base_classes.components import Component
from base_classes.components2d import Point2D

if TYPE_CHECKING:
    from components.drone import Drone


class Field(Component):
    """
    A rectangular Field on the farm.

    (left,top) .__________
               |          |
               |__________|.(right,bottom)
    """
    # Field counter
    Count = 0

    def __init__(self, simulation, top, left, bottom, right):
        """
        Initiate the field with one crop per grid point.
        """
        super().__init__(simulation)
        Field.Count = Field.Count + 1
        self.id = f"Field_{Field.Count}"

        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right

        self.crops = np.ones((right - left + 1, bottom - top + 1))  # rectangle of crops
        self.damage = 0  # total damage
        self.damagedThisStep = set()

        from components.drone import Drone
        self.protectingDrones: set[Drone] = set()
        self.patrollingPlaces = [
            Point2D(left + Drone.Radius, top + Drone.Radius),
            Point2D(right - Drone.Radius + 1, top + Drone.Radius),
            Point2D(right - Drone.Radius + 1, bottom - Drone.Radius + 1),
            Point2D(left + Drone.Radius, bottom - Drone.Radius + 1),
        ]

    def isPointInField(self, point):
        """
        Checks if the given point is inside the field.
        """
        return self.left <= point.x <= self.right and \
            self.top <= point.y <= self.bottom

    def closestPlaceToDrone(self, drone: "Drone"):
        return min(self.patrollingPlaces, key=lambda p: p.distance(drone.location))

    def assignNextPlace(self, drone: "Drone"):
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

    def assignLocationForDrone(self):
        pass

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

        # try 20 random points and see if there is an uprotected one
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

    def threat_level(self):
        birds_inside = len([
            bird for bird in self.simulation.birds
            if bird.location.is_inside(self.left, self.top, self.right, self.bottom)
        ])
        return birds_inside / len(self.simulation.birds)

    def __str__(self):
        return f"{self.id}({self.top},{self.left}),{self.bottom},{self.right})"
