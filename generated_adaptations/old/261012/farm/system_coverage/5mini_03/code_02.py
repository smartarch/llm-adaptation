from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to form group name for a field
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # Ensure "idle" group exists in allowed group_ids
        idle_group = "idle"
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not fields:
            for c in components:
                if idle_group in group_ids:
                    environment.assign_group(c, idle_group)
            return

        # Determine highest threat field (tie-break by id for determinism)
        fields_sorted = sorted(fields, key=lambda f: (-f.threat_level, str(f.id)))
        top_field = fields_sorted[0]

        # Compute field centers for distance calculations
        def field_center(f):
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0
            return cx, cy

        top_cx, top_cy = field_center(top_field)
        # Count currently assigned drones to each field (based on target_id)
        assigned_to_field = {}
        for f in fields:
            assigned_to_field[f.id] = []

        # Keep list of components not assigned to any threatened field
        others = []

        for c in components:
            tid = getattr(c, "target_id", None)
            if tid in assigned_to_field:
                assigned_to_field[tid].append(c)
            else:
                others.append(c)

        # Determine which fields are already fully protected
        fully_protected_fields = set()
        for f in fields:
            required = getattr(f, "drones_for_full_protection", 0)
            if len(assigned_to_field.get(f.id, [])) >= required:
                fully_protected_fields.add(f.id)

        # Locked drones: drones assigned to any fully protected field (they stay)
        locked_drones = set()
        # Map locked drone -> its field id
        locked_map = {}
        for fid in fully_protected_fields:
            for c in assigned_to_field.get(fid, []):
                locked_drones.add(c)
                locked_map[c] = fid

        # For the top field, compute how many more drones are needed
        top_required = getattr(top_field, "drones_for_full_protection", 0)
        top_assigned = len(assigned_to_field.get(top_field.id, []))
        # Note: drones already assigned to top_field count towards requirement (even if moving)
        need = max(0, top_required - top_assigned)

        # Build candidate pool: all drones that are not locked and not already assigned to top_field
        candidates = []
        for c in components:
            if c in locked_drones:
                continue
            # If already assigned to top field, don't consider for selection (they already count)
            if getattr(c, "target_id", None) == top_field.id:
                continue
            candidates.append(c)

        # Sort candidates by distance to top field center
        def dist_to_top(c):
            loc = getattr(c, "location", None)
            if loc is None:
                return float("inf")
            dx = loc.x - top_cx
            dy = loc.y - top_cy
            return dx * dx + dy * dy  # squared distance is fine for ordering

        candidates_sorted = sorted(candidates, key=dist_to_top)

        # Select the closest 'need' candidates
        selected_for_top = set(candidates_sorted[:need]) if need > 0 else set()

        # Now perform assignments for every component:
        for c in components:
            # If drone is locked to a fully protected field, keep it there
            if c in locked_drones:
                fid = locked_map[c]
                group = protecting_group(fid)
                if group in group_ids:
                    environment.assign_group(c, group)
                else:
                    # Fallback to idle if group missing
                    if idle_group in group_ids:
                        environment.assign_group(c, idle_group)
                continue

            # If drone is selected to protect the top field, assign it there
            if c in selected_for_top or getattr(c, "target_id", None) == top_field.id:
                group = protecting_group(top_field.id)
                if group in group_ids:
                    environment.assign_group(c, group)
                else:
                    if idle_group in group_ids:
                        environment.assign_group(c, idle_group)
                continue

            # Otherwise, assign to idle
            if idle_group in group_ids:
                environment.assign_group(c, idle_group)
            else:
                # As a last resort, try to assign to any protecting group for a threatened field (shouldn't be needed)
                fallback_assigned = False
                for f in fields:
                    g = protecting_group(f.id)
                    if g in group_ids:
                        environment.assign_group(c, g)
                        fallback_assigned = True
                        break
                if not fallback_assigned:
                    # If nothing matches, assign to first available group_id
                    if group_ids:
                        environment.assign_group(c, group_ids[0])
                    else:
                        # no-op if no group ids exist (unlikely)
                        pass