from base_classes.components import Component
from base_classes.components2d import Point2D
from components.bird import Bird
from components.drone import Drone
from components.field import Field


class SmartFarmSimulation:

    def __init__(self, adapt: callable, config: dict):

        self.fields: list[Field] = [Field(self, *coords) for coords in config["fields"]]
        self.drones: list[Drone] = [Drone(self, self.randomPoint()) for _ in range(config["drones"])]
        self.birds: list[Bird] = [Bird(self, self.randomPoint()) for _ in range(config["birds"])]

        self.components: list[Component] = self.fields + self.drones + self.birds
        self.adapt = adapt

    def run_simulation(self, steps: int):
        for step in range(steps):
            print(f"Step: {step + 1}")
            self.simulation_step()

    def simulation_step(self):
        self.adapt()

        for component in self.components:
            component.actuate()

    def randomPoint(self):
        return Point2D.random(0, 0, 100, 100)  # TODO
