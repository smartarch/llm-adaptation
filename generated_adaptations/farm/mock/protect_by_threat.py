"""Order fields by threat level and assign the closest drones to protect them."""
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        fields = sorted(environment.fields, key=lambda f: f.threat_level, reverse=True)
        drones = components
        for field in fields:
            def order(d):
                if d.target == field:
                    return 0  # Already protecting this field
                return d.location.distance(field.closestPlaceToDrone(d))

            nearest_drones = sorted(drones, key=order)
            for drone in nearest_drones[:field.drones_for_full_protection]:
                environment.assign_group(drone, f"protecting {field.id}")
                drones.remove(drone)
