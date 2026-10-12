Reasoning and adaptation strategy

- Always fully protect the single field with the highest threat_level. Keep every drone that is already targeting that primary field. If there are fewer than required, add the closest available drones to reach the required drones_for_full_protection.
- For remaining drones, opportunistically protect other threatened fields in descending threat order: keep drones already targeting those fields (unless they were taken for the primary), then add the closest available drones up to each field's requirement (partial protection accepted if not enough drones remain).
- Explicitly reassign every drone each step. Only use protecting groups that exist in group_ids; otherwise skip that field. Any drone not allocated to a protecting group becomes "idle".
- Use Euclidean distance to the field center to pick closest drones.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Strategy:
    - Fully protect the highest-threat field using the closest drones, preserving drones already targeting it.
    - Then allocate remaining drones to other threatened fields (by descending threat), preserving their
      current targeters and adding closest available drones up to each field's requirement.
    - All drones are explicitly reassigned each call (either "protecting {field.id}" or "idle").
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(c, x, y):
            lx = getattr(c.location, "x", 0.0)
            ly = getattr(c.location, "y", 0.0)
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

        # Select primary field (highest threat, tie-breaker by id)
        threatened.sort(key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        primary = threatened[0]
        primary_group = f"protecting {primary.id}"
        if primary_group not in group_ids:
            # If the primary protecting group doesn't exist, fallback to idle all
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Prepare maps
        comp_by_id = {id(c): c for c in components}
        available_ids = set(comp_by_id.keys())  # drones not yet assigned in the plan
        assigned_to_field = {}  # comp id -> field id

        # ---- Primary field allocation ----
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))

        # Keep drones already targeting primary
        kept_primary = [c for c in components if getattr(c, "target_id", None) == primary.id]
        for c in kept_primary:
            cid = id(c)
            assigned_to_field[cid] = primary.id
            available_ids.discard(cid)

        # Add closest available drones to meet required_primary
        need = required_primary - len(kept_primary)
        if need > 0 and available_ids:
            cx, cy = field_center(primary)
            avail_comps = [comp_by_id[cid] for cid in available_ids]
            avail_comps.sort(key=lambda c: distance(c, cx, cy))
            for c in avail_comps[:need]:
                cid = id(c)
                assigned_to_field[cid] = primary.id
                available_ids.discard(cid)

        # ---- Other fields allocation (descending threat) ----
        for field in threatened[1:]:
            grp = f"protecting {field.id}"
            if grp not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))

            # Keep drones already targeting this field (if still available)
            kept = []
            for cid in list(available_ids):
                c = comp_by_id[cid]
                if getattr(c, "target_id", None) == field.id:
                    kept.append(c)
            for c in kept:
                cid = id(c)
                assigned_to_field[cid] = field.id
                available_ids.discard(cid)

            # Add closest available drones to try to reach full protection
            current = sum(1 for cid, fid in assigned_to_field.items() if fid == field.id)
            need_field = required - current
            if need_field > 0 and available_ids:
                cx, cy = field_center(field)
                avail_comps = [comp_by_id[cid] for cid in available_ids]
                avail_comps.sort(key=lambda c: distance(c, cx, cy))
                for c in avail_comps[:need_field]:
                    cid = id(c)
                    assigned_to_field[cid] = field.id
                    available_ids.discard(cid)

        # Any remaining drones -> idle
        # Now perform explicit assignment for every component
        for comp in components:
            cid = id(comp)
            if cid in assigned_to_field:
                group_name = f"protecting {assigned_to_field[cid]}"
                # Safety: ensure the group exists
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    environment.assign_group(comp, idle_group)
            else:
                environment.assign_group(comp, idle_group)