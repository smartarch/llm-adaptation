from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", [])
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, mark all drones idle
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatening fields by threat level (highest first)
        threatening_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Track which drones we've assigned in this step
        assigned_ids = set()

        # For each threatening field, try to fully protect it using closest available drones
        for field in threatening_fields:
            field_id = getattr(field, "id", None)
            if field_id is None:
                continue

            required = int(getattr(field, "drones_for_full_protection", 0))

            # Count how many drones are currently protecting this field
            current_protectors = [
                d for d in components
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == field_id
            ]
            current_count = len(current_protectors)
            need = max(0, required - current_count)

            if need <= 0:
                # Already fully protected
                continue

            # Build list of candidate drones: not currently protecting any field and not already assigned
            candidates = [
                d for d in components
                if getattr(d, "state", "") != "protecting" and d.id not in assigned_ids
            ]

            if not candidates:
                continue

            # Field center for distance calculation
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            center_x = (left + right) / 2.0
            center_y = (top + bottom) / 2.0

            # Sort candidates by distance to field center (closest first)
            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                return dx*dx + dy*dy

            candidates.sort(key=lambda d: dist2(d))

            # Pick up to 'need' drones
            for d in candidates[:need]:
                environment.assign_group(d, f"protecting {field_id}")
                assigned_ids.add(d.id)

        # Finally, assign all drones not assigned in this step to idle
        for d in components:
            if d.id not in assigned_ids:
                environment.assign_group(d, "idle")