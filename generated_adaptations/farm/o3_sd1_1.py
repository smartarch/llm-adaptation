from generated_adaptations.base_classes.farm import FarmAdaptation


class AdaptiveFarm(FarmAdaptation):
    def assign_drones(self, components, environment, step: int):
        """
        Assigns drones to fields to protect crops based on the current threat levels.

        Strategy:
        1. For each field in environment.fields, compute the deficit of drones
           needed for full protection (i.e. necessary_drones_for_full_protection minus the current protecting_drones).
        2. Only consider fields that are not yet fully protected and that have a nonzero threat level.
        3. Prioritize fields by a score = threat_level * deficit.
        4. Sort fields by descending score.
        5. For each field in that order, assign as many available drones as needed (up to the deficit)
           to the group "protecting <field.id>".
        6. Any drones left over are assigned to the "idle" group.
        """
        # List of available drones (we reassign every cycle)
        available_drones = list(components)

        # List to hold (field, deficit, priority_score)
        field_needs = []
        for field in environment.fields:
            # Calculate how many drones are needed to fully protect the field.
            deficit = field.necessary_drones_for_full_protection - field.protecting_drones
            # Only consider fields that still need additional drones and have a nonzero threat.
            if deficit > 0 and field.threat_level > 0:
                priority_score = field.threat_level * deficit
                field_needs.append((field, deficit, priority_score))

        # Sort fields by descending priority score.
        field_needs.sort(key=lambda x: x[2], reverse=True)

        # Assign drones to fields based on priority.
        for field, deficit, _ in field_needs:
            group_id = "protecting " + field.id  # e.g., "protecting Field_1"
            # Assign up to the required number of drones.
            for _ in range(min(deficit, len(available_drones))):
                drone = available_drones.pop(0)
                environment.assign_group(drone, group_id)

        # Assign any remaining drones to idle.
        for drone in available_drones:
            environment.assign_group(drone, "idle")
