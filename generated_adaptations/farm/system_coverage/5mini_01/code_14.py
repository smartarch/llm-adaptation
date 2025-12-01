from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Strategy:
    - Fully protect the highest-threat field using closest drones (keep its current targeters).
    - Allocate remaining drones to other fields prioritized by threat_level / drones_for_full_protection.
    - Keep existing targeters for other fields when possible, then add closest available drones.
    - Any leftover drones -> idle. Explicit reassignment of all drones each step.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to(comp, x, y):
            lx = getattr(comp.location, "x", 0.0)
            ly = getattr(comp.location, "y", 0.0)
            return math.hypot(lx - x, ly - y)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else "idle"

        # Get fields with positive threat
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose primary: highest threat (tie-break by id)
        threatened.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        primary = threatened[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # Safety: if primary protecting group missing, idle all
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Prepare lookup and availability
        comp_by_id = {id(c): c for c in components}
        available_ids = set(comp_by_id.keys())
        assignment = {}  # comp id -> group name

        # ---- Primary allocation ----
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))

        # Keep drones already targeting primary (whether moving or protecting)
        kept_primary = [c for c in components if getattr(c, "target_id", None) == primary.id]
        for c in kept_primary:
            cid = id(c)
            assignment[cid] = primary_group
            available_ids.discard(cid)

        # Add closest available drones to meet requirement (if needed)
        need_primary = required_primary - len(kept_primary)
        if need_primary > 0 and available_ids:
            cx, cy = field_center(primary)
            avail_list = [comp_by_id[cid] for cid in available_ids]
            avail_list.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_list[:need_primary]:
                cid = id(c)
                assignment[cid] = primary_group
                available_ids.discard(cid)

        # ---- Other fields allocation ----
        other_fields = []
        for f in threatened[1:]:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            # compute value per drone (higher means more urgent per drone)
            per_drone_value = (f.threat_level / max(1, required)) if required > 0 else f.threat_level
            other_fields.append((per_drone_value, f, grp, required))

        # Sort other fields by per-drone value descending, tie-breaker by threat then id
        other_fields.sort(key=lambda t: (t[0], t[1].threat_level, getattr(t[1], "id", "")), reverse=True)

        # For each other field: keep its existing targeters (if still available), then add closest available drones up to required
        for _, field, grp, required in other_fields:
            # Keep drones already targeting this field
            kept = []
            for cid in list(available_ids):
                c = comp_by_id[cid]
                if getattr(c, "target_id", None) == field.id:
                    kept.append(c)
            for c in kept:
                cid = id(c)
                assignment[cid] = grp
                available_ids.discard(cid)

            # Determine how many more needed
            current_assigned = sum(1 for cid, g in assignment.items() if g == grp)
            need = required - current_assigned
            if need <= 0:
                continue
            if not available_ids:
                break
            cx, cy = field_center(field)
            avail_list = [comp_by_id[cid] for cid in available_ids]
            avail_list.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_list[:need]:
                cid = id(c)
                assignment[cid] = grp
                available_ids.discard(cid)

        # Any remaining drones -> idle
        for cid in list(available_ids):
            assignment[cid] = idle_group

        # Explicitly assign groups for all components
        for comp in components:
            gid = assignment.get(id(comp), idle_group)
            environment.assign_group(comp, gid)