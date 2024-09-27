from typing import Optional, TYPE_CHECKING

from base_classes.components import Component
from base_classes.components2d import Point2D
from components.bird import Bird
from components.charger import Charger
from components.drone import Drone
from components.field import Field

if TYPE_CHECKING:
    from visualizer import Visualizer


class SmartFarmSimulation:

    def __init__(self, adapt: callable, config: dict):

        self.mapWidth = config["mapWidth"]
        self.mapHeight = config["mapHeight"]

        self.fields: list[Field] = [Field(self, *coords) for coords in config["fields"]]
        self.drones: list[Drone] = [Drone(self, self.randomPoint()) for _ in range(config["drones"])]
        self.dronesDict = {drone.id: drone for drone in self.drones}
        self.birds: list[Bird] = [Bird(self, self.randomPoint()) for _ in range(config["birds"])]
        self.charger = Charger(self, config["charger"])

        self.components: list[Component] = self.fields + self.drones + self.birds + [self.charger]
        self.adapt = adapt

        self.visualizer: Optional["Visualizer"] = None

    def run_simulation(self, steps: int):
        for step in range(steps):
            print(f"Step: {step + 1}")

            self.simulation_step()

            if self.visualizer:
                self.visualizer.drawComponents(step)

    def simulation_step(self):
        self.adapt(self)

        for component in self.components:
            component.actuate()

    def randomPoint(self):
        return Point2D.random(0, 0, self.mapWidth, self.mapHeight)

    def add_visualizer(self, visualizer: "Visualizer"):
        self.visualizer = visualizer
