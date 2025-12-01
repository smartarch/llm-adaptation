from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy to protect the single most threatened field by assigning
    the closest drones (enough to reach full protection). All other drones
    are assigned to the "idle" group. If the top field is already fully
    protected, keep its protecting drones in place.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: Euclidean distance between drone and field center
        def distance_to_field_center(drone, field_center_xy):
            dx = drone.location.x - field_center_xy[0]
            dy = drone.location.y - field_center_xy[1]
            return math.hypot(dx, dy)

        # Prepare the idle group name
        idle_group = "idle"

        # Find fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened field, assign all drones to idle
        if not threatened_fields:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose the field with the highest threat level (tie broken by natural max behavior)
        target_field = max(threatened_fields, key=lambda f: f.threat_level)
        protecting_group = f"protecting {target_field.id}"

        # Number of drones required for full protection
        needed = int(getattr(target_field, "drones_for_full_protection", 0))

        # Identify drones already protecting the target field
        currently_protecting_indices = []
        for idx, comp in enumerate(components):
            if getattr(comp, "state", None) == "protecting" and comp.target_id == target_field.id:
                currently_protecting_indices.append(idx)

        # If already fully protected, keep those drones protecting and set all others idle
        if len(currently_protecting_indices) >= needed:
            # Assign current protecting drones to the protecting group (explicit re-assignment required)
            for idx, comp in enumerate(components):
                if idx in currently_protecting_indices:
                    # Only assign if the protecting group exists among valid group_ids
                    if protecting_group in group_ids:
                        environment.assign_group(comp, protecting_group)
                    else:
                        environment.assign_group(comp, idle_group)
                else:
                    environment.assign_group(comp, idle_group)
            return

        # Otherwise, select the closest drones to the target field (including any currently protecting ones)
        cx, cy = field_center(target_field)

        # Compute distances for all components
        distances = []
        for idx, comp in enumerate(components):
            dist = distance_to_field_center(comp, (cx, cy))
            distances.append((dist, idx))

        # Sort by distance and pick up to 'needed' drones
        distances.sort(key=lambda t: t[0])
        selected_indices = set(idx for (_, idx) in distances[:max(0, needed)])

        # In case some currently protecting drones exist, ensure they are included if they are among the closest.
        # (They may already be included via distance selection; we don't force-include them unless already fully protected,
        # because the requirement is to use the closest drones when building protection.)
        # Now assign groups
        for idx, comp in enumerate(components):
            if idx in selected_indices and protecting_group in group_ids:
                environment.assign_group(comp, protecting_group)
            else:
                environment.assign_group(comp, idle_group)