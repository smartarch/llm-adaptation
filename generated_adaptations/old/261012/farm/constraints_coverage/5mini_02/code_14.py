from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    """
    Allocation that:
    - Always fully protects the highest-threat field (keep existing protectors and movers).
    - Then tries to fully protect additional fields (in order of importance per drone) only when enough
      available drones exist to reach full protection for that field. Does NOT perform partial protection.
    - Explicitly assigns every drone each step and validates group names.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name if name in group_ids else "idle"

        # Threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened_fields:
            idle = valid_group("idle")
            for c in components:
                environment.assign_group(c, idle)
            return

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field(comp, field):
            cx, cy = field_center(field)
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        def field_area(field):
            return max(0.0, (field.right - field.left) * (field.bottom - field.top))

        # Build current protectors and movers by field id
        protecting_by_field = {}
        moving_by_field = {}
        for comp in components:
            state = getattr(comp, "state", "")
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target is not None:
                protecting_by_field.setdefault(target, []).append(comp)
            if state == "moving_to_field" and target is not None:
                moving_by_field.setdefault(target, []).append(comp)

        total_drones = len(components)
        half_required = ceil(total_drones / 2)

        # Choose top field by threat_level (must be fully protected)
        top_field = max(threatened_fields, key=lambda f: f.threat_level)

        # Prepare field importance score (importance per required drone)
        field_info = {}
        for f in threatened_fields:
            area = field_area(f)
            importance = getattr(f, "threat_level", 0.0) * area
            required = int(getattr(f, "drones_for_full_protection", 0))
            # treat non-positive required as 0 (nothing to assign)
            field_info[f.id] = {
                "field": f,
                "importance": importance,
                "required": max(0, required),
                "score": (importance / max(1, required)) if required > 0 else 0.0
            }

        # Selected assignment map and available drones set
        selected_assignment = {}  # comp -> field_id
        available = set(components)

        # Helper to assign chosen comps to a field and remove from available
        def assign_comps_to_field(comps_list, field_id):
            for c in comps_list:
                if c in available:
                    selected_assignment[c] = field_id
                    available.remove(c)

        # Fill a field to required with preference: current protectors -> movers -> nearest by distance
        def fill_field_to_required(field_obj, required):
            f = field_obj
            chosen = []
            # keep protectors
            for c in protecting_by_field.get(f.id, []):
                if c in available:
                    chosen.append(c)
            # add movers
            for c in moving_by_field.get(f.id, []):
                if c in available and c not in chosen:
                    chosen.append(c)
            # if still need, add nearest by distance
            if len(chosen) < required:
                need = required - len(chosen)
                candidates = [c for c in available if c not in chosen]
                candidates.sort(key=lambda c: distance_to_field(c, f))
                chosen.extend(candidates[:need])
            assign_comps_to_field(chosen, f.id)

        # Ensure top field is fully protected
        req_top = field_info[top_field.id]["required"]
        if req_top > 0:
            fill_field_to_required(top_field, req_top)

        # Prepare other fields ordered by score (importance per drone), descending
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda ff: field_info[ff.id]["score"], reverse=True)

        # Try to fully protect additional fields only if we have enough available drones to meet the remaining need.
        for f in other_fields:
            if not available:
                break
            req = field_info[f.id]["required"]
            if req <= 0:
                continue
            # Count how many of this field's protectors/movers are available (they would be kept)
            keepers = set([c for c in protecting_by_field.get(f.id, []) if c in available])
            movers = set([c for c in moving_by_field.get(f.id, []) if c in available and c not in keepers])
            # Also count any already assigned to this field (should be none unless top was same)
            already_assigned = len([c for c, fid in selected_assignment.items() if fid == f.id])
            current_if_kept = already_assigned + len(keepers) + len(movers)
            required_remaining = max(0, req - current_if_kept)
            # Only proceed if we have enough available drones to fulfill the remaining requirement
            if required_remaining == 0:
                # can be completed by keepers/movers alone; perform assignment to ensure protectors/movers are assigned
                fill_field_to_required(f, req)
            elif len(available) >= required_remaining:
                # We can fully protect this field: assign keepers/movers plus nearest required_remaining drones
                fill_field_to_required(f, req)
            else:
                # Not enough drones to fully protect this field, skip (no partial protection)
                continue
            # Stop early if we already reached half_required of drones protecting (optional utilization target)
            if len(selected_assignment) >= half_required:
                break

        # All remaining drones remain idle (we avoid partial protection)

        # Prepare group names and assign groups explicitly
        idle_group = valid_group("idle")
        protecting_group_cache = {f.id: valid_group(f"protecting {f.id}") for f in threatened_fields}

        for comp in components:
            if comp in selected_assignment:
                gid = protecting_group_cache.get(selected_assignment[comp], idle_group)
                environment.assign_group(comp, gid)
            else:
                environment.assign_group(comp, idle_group)