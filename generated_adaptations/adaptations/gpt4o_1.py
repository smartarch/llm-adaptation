import random

from base_classes.adaptation import Adaptation


class Strategy(Adaptation):
    def adapt(self, simulation, step: int):
        for drone in simulation.availableDrones():
            if drone.battery < 0.25:
                drone.assignTarget(simulation.charger)
            elif drone.target is None:
                drone.assignTarget(random.choice(simulation.fields))
