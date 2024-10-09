import random
from typing import TYPE_CHECKING

from base_classes.adaptation import Adaptation
from components.drone import DroneState

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class FakeAdaptation(Adaptation):

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        for drone in simulation.drones:
            if drone.state == DroneState.TERMINATED:
                continue
            if drone.battery < 0.25:
                drone.assignTarget(simulation.charger)
            elif drone.target is None:
                drone.assignTarget(random.choice(simulation.fields))
