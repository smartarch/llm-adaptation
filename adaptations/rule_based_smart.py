import random

from base_classes.adaptation import Adaptation
from components.drone import DroneState
from simulation import SmartFarmSimulation, notTerminatedDrones


class RuleBasedFullNearestAdaptation(Adaptation):
    """Protects the most threatened fields with nearest drones."""

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        available_drones = set(notTerminatedDrones(simulation))
        drones_to_charge = [d for d in available_drones if d.battery < 0.25]

        for drone in drones_to_charge:
            drone.assignTarget(simulation.charger)
            available_drones.remove(drone)

        for field in sorted(simulation.fields, key=lambda f: f.threat_level(), reverse=True):
            if len(available_drones) == 0:
                break

            closest_drones = sorted(available_drones, key=lambda d: d.location.distance(field.closestPlaceToDrone(d)))
            for drone in closest_drones[:field.necessary_drones_for_full_protection]:
                drone.assignTarget(field)
                available_drones.remove(drone)


class RuleBasedProtectOneAdaptation(Adaptation):
    """Protects the most threatened field with nearest idle drones. The remaining drones are idle."""

    def __init__(self):
        self.standby_drones = []
        self.active_drones = []
        self.currently_protecting_field = None
        self.last_protected_field = None

    def init(self, simulation: "SmartFarmSimulation"):
        # FIXME: this assumes 8 drones
        self.active_drones = simulation.drones[:4]
        self.standby_drones = simulation.drones[4:]

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        field = max(simulation.fields, key=lambda f: f.threat_level())

        if field == self.currently_protecting_field:
            return

        self.last_protected_field = self.currently_protecting_field
        self.currently_protecting_field = field

        # assign standby drones to the new target to protect
        for drone in self.standby_drones:
            drone.assignTarget(field)

        # swap active and standby drones
        self.standby_drones, self.active_drones = self.active_drones, self.standby_drones

        # TODO: if we have to charge the drones, we can start charging the standby drones now
