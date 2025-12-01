Strategy (brief)

Goal: fully protect the highest-threat field using the closest drones (keeping drones already targeting it). Instead of leaving all remaining drones idle, opportunistically allocate remaining drones to other threatened fields to reduce aggregate damage. For those other fields we:
- keep drones already targeting them (if still available),
- compute remaining need = drones_for_full_protection - kept_count,
- prioritize fields by threat_level / max(1, remaining_need) so high-threat small-need fields get drones first,
- allocate the closest available drones up to remaining_need (partial protection allowed).
All drones are explicitly reassigned each step. Protecting groups are only used if present in group_ids; otherwise fields are skipped. If primary protecting group is missing we assign all drones to idle.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Allocation strategy:
    - Fully protect the highest-threat field using closest drones, keeping any already targeting it.
    - Allocate remaining drones to other threatened fields by priority (threat / remaining_need),
      keeping their existing targeters first and adding closest drones up to need (partial protection allowed).
    - Any leftover drones -> idle.
    - Explicitly reassign every drone each call.
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

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Select primary field (highest threat, tie-break by id)
        threatened.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        primary = threatened[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # Cannot use primary protecting group -> idle all
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Prepare component maps and availability
        comp_by_id = {id(c): c for c in components}
        available_ids = set(comp_by_id.keys())
        assignment = {}  # comp id -> group id

        # ---- Primary field allocation ----
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))
        # Keep drones already targeting primary
        kept_primary = [c for c in components if getattr(c, "target_id", None) == primary.id]
        for c in kept_primary:
            cid = id(c)
            assignment[cid] = primary_group
            available_ids.discard(cid)

        # Add closest available drones to meet requirement
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
            # Count kept among currently available
            kept = [comp_by_id[cid] for cid in list(available_ids) if getattr(comp_by_id[cid], "target_id", None) == f.id]
            kept_count = len(kept)
            remaining_need = max(0, required - kept_count)
            if f.threat_level <= 0:
                continue
            # Priority: threat / max(1, remaining_need) so fields needing fewer drones and higher threat come first
            priority = f.threat_level / max(1, remaining_need)
            other_fields.append((priority, f, grp, required, kept))

        other_fields.sort(key=lambda t: t[0], reverse=True)

        # Assign kept drones for other fields first
        for _, f, grp, required, kept in other_fields:
            for c in kept:
                cid = id(c)
                if cid in available_ids:
                    assignment[cid] = grp
                    available_ids.discard(cid)

        # Allocate additional drones to meet remaining needs in priority order
        for _, f, grp, required, kept in other_fields:
            current = sum(1 for cid, g in assignment.items() if g == grp)
            need = max(0, required - current)
            if need <= 0 or not available_ids:
                continue
            cx, cy = field_center(f)
            avail_list = [comp_by_id[cid] for cid in available_ids]
            avail_list.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_list[:need]:
                cid = id(c)
                assignment[cid] = grp
                available_ids.discard(cid)

        # Remaining drones -> idle
        for cid in list(available_ids):
            assignment[cid] = idle_group

        # Explicitly assign groups for all components
        for comp in components:
            gid = assignment.get(id(comp), idle_group)
            environment.assign_group(comp, gid)