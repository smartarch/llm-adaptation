Strategy reasoning

We must always fully protect the single field with the highest threat using the closest drones (and keep drones already targeting that field). To improve over previous versions, I avoid leaving many drones idle: after protecting the primary field, remaining drones are allocated to other threatened fields in a way that prioritizes the best marginal benefit per drone:

- For each other field, count how many drones already target it (and are still available) — keep those.
- Compute remaining_need = drones_for_full_protection - kept_count.
- Prioritize fields by (threat_level / remaining_need) so fields that are more threatened and need fewer extra drones get assigned first.
- For each prioritized field, assign the closest available drones (by Euclidean distance to field center) up to its remaining_need (partial protection accepted).
- Any drones left after these allocations become idle.
- Every drone is explicitly reassigned each call. We only use protecting groups present in group_ids; otherwise we skip those fields. Primary protecting group must exist or we idle all.

This keeps existing protections, uses closest drones for the primary field, and spreads remaining capacity to fields where each extra drone reduces expected damage the most.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Allocation strategy:
    - Fully protect the highest-threat field using the closest drones (keep any already targeting it).
    - Allocate remaining drones to other threatened fields by priority = threat_level / remaining_need,
      keeping their existing targeters first and adding closest drones up to their need (partial protection allowed).
    - Any leftover drones -> idle.
    - Explicitly reassign every drone each step.
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

        # Threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # Nothing to protect
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose primary: highest threat_level (tie-break by id)
        threatened.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        primary = threatened[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # Cannot protect primary (group absent) -> idle all
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Setup maps and available set
        comp_by_id = {id(c): c for c in components}
        available_ids = set(comp_by_id.keys())
        assignment = {}  # comp id -> group id

        # ---- Primary field: keep its current targeters, then add closest to meet requirement ----
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))
        # Keep all drones already targeting primary
        kept_primary = [c for c in components if getattr(c, "target_id", None) == primary.id]
        for c in kept_primary:
            cid = id(c)
            assignment[cid] = primary_group
            available_ids.discard(cid)

        # If fewer than required, add closest available drones
        need = required_primary - len(kept_primary)
        if need > 0 and available_ids:
            cx, cy = field_center(primary)
            avail_comps = [comp_by_id[cid] for cid in available_ids]
            avail_comps.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_comps[:need]:
                cid = id(c)
                assignment[cid] = primary_group
                available_ids.discard(cid)

        # ---- Other fields: compute remaining_need and priority, then allocate greedily ----
        other_fields = []
        for f in threatened[1:]:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            # kept among currently available (we haven't assigned them elsewhere)
            kept = [comp_by_id[cid] for cid in list(available_ids) if getattr(comp_by_id[cid], "target_id", None) == f.id]
            kept_count = len(kept)
            remaining_need = max(0, required - kept_count)
            # Only consider fields with threat > 0
            if f.threat_level <= 0:
                continue
            # Priority: higher threat and smaller remaining_need get higher priority.
            # If remaining_need == 0, priority = threat_level (they're already covered by kept)
            priority = f.threat_level / max(1, remaining_need) if remaining_need > 0 else f.threat_level
            other_fields.append((priority, f, grp, required, kept))

        # Sort fields by priority descending
        other_fields.sort(key=lambda t: t[0], reverse=True)

        # Assign kept first (they remain on their fields)
        for _, f, grp, required, kept in other_fields:
            for c in kept:
                cid = id(c)
                # keep only if still available (may be used for primary)
                if cid in available_ids:
                    assignment[cid] = grp
                    available_ids.discard(cid)

        # Now allocate additional drones to meet remaining needs in order
        for _, f, grp, required, kept in other_fields:
            # count how many already assigned to this field (kept may have been assigned above)
            current = sum(1 for cid, g in assignment.items() if g == grp)
            remaining_need = max(0, required - current)
            if remaining_need <= 0:
                continue
            if not available_ids:
                break
            cx, cy = field_center(f)
            avail_comps = [comp_by_id[cid] for cid in available_ids]
            avail_comps.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_comps[:remaining_need]:
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