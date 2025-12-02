# Adaptation strategy reasoning (embedded as comments for traceability)
#
# Objective:
# - Always fully protect the highest-threat field using the closest drones.
# - Minimize unnecessary drone reassignments to keep protection stable.
# - Ensure every drone is assigned to exactly one valid group in every step.
#
# Strategy details:
# - Identify fields with threat_level > 0 and pick the top-threat field.
# - Determine how many drones are currently protecting that top field.
# - If fewer drones than required (drones_for_full_protection), allocate the closest
#   available drones to the top field until full protection is achieved.
# - Keep drones protecting other fields if possible to minimize churn; only reassign
#   them if their target field is no longer threatened or the group is invalid.
# - Always validate that a requested "protecting {field_id}" group exists in group_ids
#   before assigning to it. If not, fallback to "idle" for safety.
# - Use the field centers to compute distances for "closest" drone selection.
#
# This implementation adheres to the API contract and aims to satisfy the unit tests
# by enforcing full protection for the top field and reducing excessive reassignments.

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist2(drone, x, y):
            dx = getattr(drone.location, "x", 0.0) - x
            dy = getattr(drone.location, "y", 0.0) - y
            return dx * dx + dy * dy

        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no field is threatened, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat_level (desc), stable by id
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
            reverse=True,
        )

        top_field = threat_fields_sorted[0]
        top_field_id = getattr(top_field, "id", None)
        top_center_x, top_center_y = field_center(top_field)

        # Current drones protecting the top field
        current_top_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id
        ]

        drones_for_top = getattr(top_field, "drones_for_full_protection", 0)
        need_top = max(0, int(drones_for_top) - int(len(current_top_protecting)))

        # Validate group name existence
        top_group = f"protecting {top_field_id}"
        top_group_valid = top_group in set(group_ids)

        # Build the set of drones that will protect the top field
        top_protecting = list(current_top_protecting)

        if need_top > 0:
            candidates = [d for d in components if d not in top_protecting]
            candidates.sort(key=lambda d: dist2(d, top_center_x, top_center_y))
            for d in candidates[:need_top]:
                top_protecting.append(d)

        # Assign groups
        for d in components:
            if d in top_protecting:
                if top_group_valid:
                    environment.assign_group(d, top_group)
                else:
                    # If the group is not recognized, fall back to idle to avoid errors
                    environment.assign_group(d, "idle")
            else:
                # If a drone is currently protecting some field, try to keep it if that field is still threatened
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                    tgt_id = d.target_id
                    tgt_field = next((f for f in fields if getattr(f, "id", None) == tgt_id), None)
                    if tgt_field is not None and getattr(tgt_field, "threat_level", 0) > 0:
                        tgt_group = f"protecting {tgt_id}"
                        if tgt_group in set(group_ids):
                            environment.assign_group(d, tgt_group)
                        else:
                            environment.assign_group(d, "idle")
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")