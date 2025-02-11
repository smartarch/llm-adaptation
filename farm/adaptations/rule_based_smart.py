from base_classes.adaptation import Adaptation
from farm.simulation import SmartFarmSimulation


class RuleBasedFullNearestAdaptation(Adaptation):
    """Protects the most threatened fields with nearest drones."""

    def __init__(self, adapt_every=1):
        self.adapt_every = adapt_every

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        available_drones = set(simulation.availableDrones())
        drones_to_charge = [d for d in available_drones if d.battery < 0.25]

        for drone in drones_to_charge:
            drone.assignTarget(simulation.charger)
            available_drones.remove(drone)

        for field in self.fieldsByThreatLevel(simulation):
            if len(available_drones) == 0:
                break

            closest_drones = sorted(available_drones, key=lambda d: d.location.distance(field.closestPlaceToDrone(d)))
            for drone in closest_drones[:field.necessary_drones_for_full_protection]:
                drone.assignTarget(field)
                available_drones.remove(drone)

    @staticmethod
    def fieldsByThreatLevel(simulation):
        return sorted(simulation.fields, key=lambda f: f.threat_level, reverse=True)


class RuleBasedFullNearestOracleAdaptation(RuleBasedFullNearestAdaptation):

    @staticmethod
    def fieldsByThreatLevel(simulation):
        # get the true bird probabilities from an oracle
        oracleAttackProbabilities = simulation.fieldProbabilityGenerator()
        return [f for _, f in sorted(zip(oracleAttackProbabilities, simulation.fields), key=lambda f: f[0], reverse=True)]


class RuleBasedProtectOneAdaptation(Adaptation):
    """Protects the most threatened field with nearest idle drones. The remaining drones are idle."""

    def __init__(self):
        self.standby_drones = []
        self.active_drones = []
        self.currently_protecting_field = None
        self.last_protected_field = None
        self.charging = False

    def init(self, simulation: "SmartFarmSimulation"):
        # FIXME: this assumes 8 drones
        self.active_drones = simulation.drones[:4]
        self.standby_drones = simulation.drones[4:]
        self.charging = ("noCharging" not in simulation.config or not simulation.config["noCharging"])

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        field = max(simulation.fields, key=lambda f: f.threat_level)

        if field == self.currently_protecting_field:
            return

        self.last_protected_field = self.currently_protecting_field
        self.currently_protecting_field = field

        if self.charging:
            # use the group with more average battery as active
            active_battery = sum(d.battery for d in self.active_drones) / len(self.active_drones)
            standby_battery = sum(d.battery for d in self.standby_drones) / len(self.standby_drones)

            if standby_battery > active_battery:
                self.active_drones, self.standby_drones = self.standby_drones, self.active_drones
        else:
            # use standby drones for new field (swap groups)
            self.standby_drones, self.active_drones = self.active_drones, self.standby_drones

        for drone in self.active_drones:
            drone.assignTarget(field)

        if self.charging:
            for drone in self.standby_drones:
                drone.assignTarget(simulation.charger)
