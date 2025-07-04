import random
from typing import TYPE_CHECKING

from base_classes.adaptation import Adaptation
from farm.components.drone import DroneState

if TYPE_CHECKING:
    from farm.simulation import SmartFarmSimulation


class RuleBasedRandomAdaptation(Adaptation):

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        for drone in simulation.availableDrones():
            if drone.battery < 0.25:
                drone.assignTarget(simulation.charger)
            elif drone.target is None:
                field = random.choice(simulation.fields)
                # drone.assignTarget(field)
                simulation.assign_group(drone, f"protecting {field.id}")


class RuleBasedField2Adaptation(Adaptation):
    """Protect only Field 2."""
    DronesRequired = 6

    def __init__(self):
        super().__init__()
        self.assigned = 0

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        drones = [d for d in
                  sorted(simulation.drones, key=lambda d: -d.battery)
                  if d.state == DroneState.IDLE]
        if self.assigned < self.DronesRequired:
            for drone in drones[:self.DronesRequired - self.assigned]:
                drone.assignTarget(simulation.fields[1])
                self.assigned += 1

        protecting = list(simulation.fields[1].protectingDrones)
        for drone in protecting:
            if drone.battery <= 0.16:
                drone.assignTarget(simulation.charger)
                self.assigned -= 1
            elif drone.battery <= 0.22:
                for new_drone in drones:
                    if new_drone.state == DroneState.IDLE:
                        new_drone.assignTarget(simulation.fields[1])
                        self.assigned += 1
        # print(self.assigned)
