"""Assign drones to fully protect the most threatened field. Keep other drones where they were."""
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        most_threatened = max(environment.fields, key=lambda f: f.threat_level)
        nearest_drones = sorted(components, key=lambda d: d.location.distance(most_threatened.closestPlaceToDrone(d)))
        for drone in nearest_drones[:most_threatened.drones_for_full_protection]:
            # drone.assignTarget(field)
            environment.assign_group(drone, f"protecting {most_threatened.id}")
            nearest_drones.remove(drone)

        for drone in nearest_drones:
            if drone.target:
                environment.assign_group(drone, f"protecting {drone.target.id}")
            else:
                environment.assign_group(drone, f"idle")

