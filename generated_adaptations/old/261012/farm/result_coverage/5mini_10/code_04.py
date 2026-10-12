from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper functions
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist2(loc, cx, cy):
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # Prepare threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if f.threat_level > 0]
        if not threatened:
            # No threats: set all drones to idle (if available)
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
            return

        # Sort fields by descending threat_level, tie-breaker by id (string) for determinism
        threatened.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Map drone -> chosen group (we'll call environment.assign_group at the end or as we pick)
        # But to respect "keep protecting if already protecting", we will immediately assign when choosing.
        # Track which drones have been assigned in this adaptation call.
        assigned_drones = set()

        # Create a working list of available drones (initially all)
        available = list(components)

        # Precompute field centers
        centers = {f.id: field_center(f) for f in threatened}

        # Greedily fully protect as many fields as possible in order of threat
        for field in threatened:
            # Ensure group name exists
            target_group = f"protecting {field.id}"
            if target_group not in group_ids:
                # If protecting group not available (shouldn't happen), skip field
                continue

            required = int(field.drones_for_full_protection)
            if required <= 0:
                required = 1

            cx, cy = centers[field.id]

            # Count drones among available that are already protecting this field
            already_protecting = [d for d in available if d.state == "protecting" and d.target_id == field.id]
            # Assign those first (keep them)
            for d in already_protecting:
                environment.assign_group(d, target_group)
                assigned_drones.add(d)
            # Remove them from available
            available = [d for d in available if d not in assigned_drones]

            protected_count = len(already_protecting)
            need = max(0, required - protected_count)
            if need == 0:
                # Field already fully protected; continue to next field
                continue

            # Candidates among available drones
            # Prefer drones moving to this field
            moving_to_field = [d for d in available if d.state == "moving_to_field" and d.target_id == field.id]
            others = [d for d in available if not (d.state == "moving_to_field" and d.target_id == field.id)]

            # Sort by distance to field center
            moving_to_field.sort(key=lambda d: dist2(d.location, cx, cy))
            others.sort(key=lambda d: dist2(d.location, cx, cy))

            selected = []
            for d in moving_to_field:
                if len(selected) >= need:
                    break
                selected.append(d)
            for d in others:
                if len(selected) >= need:
                    break
                selected.append(d)

            # If not enough candidates to fully protect this field, do not partially protect it:
            # we prefer to leave drones idle or use them for lower-priority fields only if they can fully protect.
            if len(selected) < need:
                # Do not assign these selected drones to a partial protecting group.
                # Leave them available for potentially protecting lower-priority fields (or idle).
                # Continue to next field without assigning more here.
                continue

            # Assign selected drones to this field
            for d in selected:
                environment.assign_group(d, target_group)
                assigned_drones.add(d)

            # Remove them from available
            available = [d for d in available if d not in assigned_drones]

            # If no drones remain, break early
            if not available:
                break

        # Any remaining drones -> idle
        for d in components:
            if d in assigned_drones:
                continue
            if "idle" in group_ids:
                environment.assign_group(d, "idle")