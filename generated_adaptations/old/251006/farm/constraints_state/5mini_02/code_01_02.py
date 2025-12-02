from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy that always fully protects the field with the highest threat level
    using the closest drones. Drones already assigned (target_id == field.id) are treated as
    committed to that field. Remaining drones become idle unless they are selected to fill
    the needed count for full protection.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute Euclidean distance
        def dist(p1, p2):
            return math.hypot(p1.x - p2[0], p1.y - p2[1])

        # Collect fields with positive threat
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
            return

        # Compute swarm center (average drone location) for tie-breaking
        drone_locations = [(c.location.x, c.location.y) for c in components if getattr(c, "location", None) is not None]
        if drone_locations:
            avg_x = sum(x for x, _ in drone_locations) / len(drone_locations)
            avg_y = sum(y for _, y in drone_locations) / len(drone_locations)
            swarm_center = (avg_x, avg_y)
        else:
            swarm_center = (0.0, 0.0)

        # Choose the field with highest threat_level; tie-break by distance to swarm center
        def field_sort_key(f):
            # higher threat first, then smaller distance to swarm center
            center = ((getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0,
                      (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0)
            d = math.hypot(center[0] - swarm_center[0], center[1] - swarm_center[1])
            return (getattr(f, "threat_level", 0), -d)

        # pick field with max threat, tie-break handled by key
        target_field = max(fields, key=field_sort_key)

        # Prepare target group name and verify existence
        target_group = f"protecting {target_field.id}"
        if target_group not in group_ids:
            # Fallback to idle if the protecting group isn't available
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        # Field center for distance calculations
        field_center = ((getattr(target_field, "left", 0) + getattr(target_field, "right", 0)) / 2.0,
                        (getattr(target_field, "top", 0) + getattr(target_field, "bottom", 0)) / 2.0)

        # Determine how many drones are required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Find drones already committed to that field (target_id == field.id)
        committed = []
        uncommitted = []
        for comp in components:
            if getattr(comp, "target_id", None) == target_field.id:
                committed.append(comp)
            else:
                uncommitted.append(comp)

        committed_count = len(committed)
        need_additional = max(0, required - committed_count)

        # Sort uncommitted drones by distance to field center and pick needed ones
        uncommitted_sorted = sorted(uncommitted, key=lambda c: dist(c.location, field_center))
        selected_for_protect = uncommitted_sorted[:need_additional]

        # Assign groups: committed + selected -> protecting group; others -> idle
        protecting_set = set(committed) | set(selected_for_protect)
        for comp in components:
            if comp in protecting_set:
                environment.assign_group(comp, target_group)
            else:
                # assign to idle if available
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # fallback: if idle not present, try to assign to any protecting group (unlikely)
                    environment.assign_group(comp, target_group)