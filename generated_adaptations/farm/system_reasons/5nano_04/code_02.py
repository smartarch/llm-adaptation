import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones to groups for protecting fields.

        Components: list of drone components.
        environment: provides fields and a method assign_group(component, group_id).
        group_ids: list of valid group names (e.g., "idle", "protecting {field.id}").
        step: current time step (not used directly but available if needed).
        """
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            # No threat -> idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda fl: fl.threat_level, reverse=True)
        top_field = fields_sorted[0]

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Group name for top field
        top_group = f"protecting {top_field.id}"

        # Count drones currently protecting the top field (based on current state)
        current_top = sum(1 for d in components if (getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id))

        # Drones needed for full protection of top field
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # Build candidate drones to assign to the top field (exclude those already protecting it)
        top_center = field_center(top_field)
        def dist_to_top(d):
            x = getattr(d.location, "x", 0)
            y = getattr(d.location, "y", 0)
            dx = x - top_center[0]
            dy = y - top_center[1]
            return math.hypot(dx, dy)

        candidates_for_top = [d for d in components if not (getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id)]
        candidates_for_top.sort(key=dist_to_top)

        # Prepare final desired group for every drone
        desired_group = {d: "idle" for d in components}

        # Assign the closest drones to top field to reach full protection
        to_top = min(needed_top, len(candidates_for_top))
        for i in range(to_top):
            desired_group[candidates_for_top[i]] = top_group

        # Now allocate remaining idle drones to other threatened fields to achieve full protection
        # Compute current plan counts per field based on desired_group
        field_counts = {}
        for field in fields_sorted:
            fid = field.id
            field_counts[fid] = sum(1 for d in components if desired_group.get(d, "idle") == f"protecting {fid}")

        # Idle drones available for allocation to other fields
        idle_drones = [d for d in components if desired_group.get(d, "idle") == "idle"]

        # For each remaining field (in threat order), allocate idle drones to fully protect if possible
        for field in fields_sorted[1:]:
            fid = field.id
            current = field_counts.get(fid, 0)
            needed = max(0, field.drones_for_full_protection - current)
            if needed <= 0:
                continue

            center = field_center(field)

            def dist_to_field(d):
                x = getattr(d.location, "x", 0)
                y = getattr(d.location, "y", 0)
                dx = x - center[0]
                dy = y - center[1]
                return math.hypot(dx, dy)

            # Sort idle drones by distance to this field
            idle_sorted = sorted(idle_drones, key=dist_to_field)

            assign_count = min(needed, len(idle_sorted))
            for i in range(assign_count):
                d = idle_sorted[i]
                desired_group[d] = f"protecting {fid}"

            # Remove newly assigned drones from idle pool
            for i in range(assign_count):
                idle_drones.remove(idle_sorted[i])

            # Update field_counts for this field
            field_counts[fid] = field_counts.get(fid, 0) + assign_count

        # Finally, apply the final group assignments to all drones
        for d in components:
            env_group = desired_group.get(d, "idle")
            environment.assign_group(d, env_group)