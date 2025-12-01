Reasoning and adaptation strategy

Goal: always fully protect the highest-threat field using the closest drones, and make better use of remaining drones by allocating them to other threatened fields (in descending threat order), keeping any drones already targeting each field. This reduces total damage by providing partial protection where full protection isn't possible. Key points:

- Select primary = field with highest threat_level (tie-break by id).
- Keep all drones already targeting the primary field. If that is fewer than required, add the closest available drones until the required number is reached. If already more than required, keep them all (do not reassign away).
- For other threatened fields (by descending threat), keep drones already targeting them (that remain available), then add closest available drones to try to reach full protection. Partial protection is accepted.
- Explicitly assign every drone each step either to "protecting {field.id}" or to "idle".
- Respect group_ids: only use protecting groups that exist; if the primary protecting group is missing, assign all drones to idle.

Implementation (single Python code block):

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved strategy:
    - Fully protect the highest-threat field using closest drones, keeping drones already targeting it.
    - Allocate remaining drones to other threatened fields (descending threat), keeping their targeters first,
      and adding closest available drones to try to reach full protection (partial protection allowed).
    - Explicitly reassign every drone each call.
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to(comp, x, y):
            lx = getattr(comp.location, "x", 0.0)
            ly = getattr(comp.location, "y", 0.0)
            return math.hypot(lx - x, ly - y)

        idle_group = "idle"
        if idle_group not in group_ids:
            idle_group = group_ids[0] if group_ids else "idle"

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Sort by threat desc, then id for tie-break
        threatened.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        primary = threatened[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # Can't protect primary if group missing -> idle all
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Mapping and available set by id for stable tracking
        comp_by_id = {id(c): c for c in components}
        available_ids = set(comp_by_id.keys())
        assignment = {}  # comp id -> group id

        # ---- Primary field allocation ----
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))
        # Keep all drones already targeting primary
        kept_primary = [c for c in components if getattr(c, "target_id", None) == primary.id]
        for c in kept_primary:
            cid = id(c)
            assignment[cid] = primary_group
            if cid in available_ids:
                available_ids.remove(cid)

        # If fewer than required, add closest available drones to reach requirement
        need_primary = required_primary - len(kept_primary)
        if need_primary > 0:
            cx, cy = field_center(primary)
            avail_comps = [comp_by_id[cid] for cid in available_ids]
            avail_comps.sort(key=lambda c: distance_to(c, cx, cy))
            for c in avail_comps[:need_primary]:
                cid = id(c)
                assignment[cid] = primary_group
                available_ids.discard(cid)

        # ---- Other fields allocation (descending threat) ----
        for field in threatened[1:]:
            grp = f"protecting {field.id}"
            if grp not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            # Keep drones already targeting this field (and still available)
            kept = []
            for cid in list(available_ids):
                c = comp_by_id[cid]
                if getattr(c, "target_id", None) == field.id:
                    kept.append(c)
                    assignment[cid] = grp
                    available_ids.discard(cid)
            # If still need more, pick closest available
            need = required - len(kept)
            if need > 0 and available_ids:
                cx, cy = field_center(field)
                avail_comps = [comp_by_id[cid] for cid in available_ids]
                avail_comps.sort(key=lambda c: distance_to(c, cx, cy))
                for c in avail_comps[:need]:
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