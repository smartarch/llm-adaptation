Reasoning and strategy

What I changed and why

The previous versions often moved many drones around trying to optimize complex scores, which caused instability and left other fields unprotected for longer. To reduce damage I switch to a simpler, more conservative strategy that focuses on three things:

1. Strictly enforce the hard requirement: the single most threatened field must always be fully protected by the closest drones. To satisfy "closest drones" precisely, we select the k closest drones (by Euclidean distance to the field center) and assign them to that field. This minimizes the time until that critical field becomes fully protected.

2. Preserve ongoing protections elsewhere where possible. After selecting the top-field drones, I keep existing protectors on their fields (based on our previous assignment record and the drone's observed state/target) rather than stealing them. If a field currently has more protectors than required we trim the farthest ones. This limits churn and avoids opening multiple fields to damage simultaneously.

3. Use idle (or currently idle-like) drones to extend protection to other fields only if they can fully protect another field (no partial protection). I assign additional fields by descending threat using available idle drones and picking the closest idle drones for those fields. I avoid forcing reassignments from other protected fields unless required for the top field selection. This keeps most drones actively protecting while minimizing unnecessary moves.

This approach is intentionally conservative: it strictly minimizes time to protect the top field (highest immediate benefit) and otherwise keeps protections in place to prevent oscillation. It uses idle resources to expand protection selectively and never overprotects a field.

Code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict
from typing import Any

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # drone id -> (last_group, consecutive_steps)
        self._prev = {}

    def _center(self, field: Any):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total = len(drones)

        # helper for group name
        def protecting_gid(fid):
            return f"protecting {fid}"

        # gather fields with positive threat
        fields_all = list(environment.fields)
        fields = [f for f in fields_all if getattr(f, "threat_level", 0.0) > 0.0]
        centers = {f.id: self._center(f) for f in fields}

        # build drone metadata
        drone_meta = []
        for d in drones:
            did = id(d)
            prev_group, prev_steps = self._prev.get(did, (None, 0))
            loc = getattr(d, "location", None)
            x = getattr(loc, "x", 0.0) if loc is not None else 0.0
            y = getattr(loc, "y", 0.0) if loc is not None else 0.0
            drone_meta.append({
                "obj": d,
                "id": did,
                "x": x,
                "y": y,
                "state": getattr(d, "state", None),
                "target_id": getattr(d, "target_id", None),
                "prev_group": prev_group,
                "prev_steps": prev_steps,
            })

        # final assignment mapping: drone id -> group
        final_assign = {}

        # If no threatened fields: idle everything
        if not fields:
            for dm in drone_meta:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(dm["obj"], assigned)
                last_group, last_steps = self._prev.get(dm["id"], (None, 0))
                if last_group == assigned:
                    self._prev[dm["id"]] = (assigned, last_steps + 1)
                else:
                    self._prev[dm["id"]] = (assigned, 1)
            return

        # determine top (most threatened) field
        fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = fields[0]
        top_gid = protecting_gid(top_field.id)
        k_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # compute distance for each drone to a field center
        def dist_to_field(dm, fid):
            cx, cy = centers[fid]
            return self._dist(dm["x"], dm["y"], cx, cy)

        # 1) Assign the closest k_top drones to the top field (strict closeness)
        if k_top > 0 and top_gid in group_ids:
            # sort all drones by distance to top_field
            sorted_all = sorted(drone_meta, key=lambda dm: dist_to_field(dm, top_field.id))
            chosen_top = sorted_all[:min(k_top, len(sorted_all))]
            for dm in chosen_top:
                final_assign[dm["id"]] = top_gid

        # helper: available drones not yet assigned
        def available():
            return [dm for dm in drone_meta if dm["id"] not in final_assign]

        # 2) Preserve existing protectors on other fields where possible.
        # For each other field, collect drones that were previously assigned to that protecting group
        # or are currently protecting/moving to that field (based on state/target), and keep them assigned,
        # trimming if they exceed required number (keep the closest ones).
        for f in fields:
            if f.id == top_field.id:
                continue
            gid = protecting_gid(f.id)
            if gid not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # collect candidates from those not already re-assigned to top field
            cand = []
            for dm in available():
                # prefer drones we previously assigned to this group
                if dm["prev_group"] == gid:
                    cand.append(dm)
                # also include drones currently protecting/moving to this target
                elif dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == f.id:
                    cand.append(dm)
            if not cand:
                continue
            # if more than required keep the closest ones (to avoid overprotection)
            cand.sort(key=lambda dm: dist_to_field(dm, f.id))
            keep = cand[:required]
            for dm in keep:
                final_assign[dm["id"]] = gid

        # 3) Use idle drones to fully protect additional fields (no stealing from other protected fields).
        # Identify idle-like drones: those not assigned yet and either prev_group == "idle" or state == "idle".
        def idle_candidates():
            return [dm for dm in available() if (dm["prev_group"] == "idle" or dm["state"] == "idle" or dm["prev_group"] is None)]
        idle_pool = idle_candidates()

        # attempt to fully protect additional fields in descending threat order using idle drones only
        remaining_fields = [f for f in fields if f.id != top_field.id]
        remaining_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        for f in remaining_fields:
            gid = protecting_gid(f.id)
            if gid not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # count already assigned to this field (from step 2)
            already = sum(1 for did, g in final_assign.items() if g == gid)
            need = required - already
            if need <= 0:
                continue
            # if enough idle drones to fully protect this field, assign the closest idle drones
            if len(idle_pool) >= need:
                # sort idle_pool by distance to field center
                idle_pool.sort(key=lambda dm: dist_to_field(dm, f.id))
                chosen = idle_pool[:need]
                for dm in chosen:
                    final_assign[dm["id"]] = gid
                # remove chosen from idle_pool
                idle_pool = [dm for dm in idle_pool if dm["id"] not in final_assign]
            # otherwise skip this field (no partial protection)

        # 4) After these steps, do not aggressively steal drones from other protections.
        # If we still have unassigned drones, put them to idle.
        for dm in drone_meta:
            if dm["id"] not in final_assign:
                final_assign[dm["id"]] = "idle"

        # 5) Commit assignments and update prev tracking
        for dm in drone_meta:
            obj = dm["obj"]
            did = dm["id"]
            assigned = final_assign.get(did, "idle")
            # validate group id
            if assigned not in group_ids:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            environment.assign_group(obj, assigned)
            last_group, last_steps = self._prev.get(did, (None, 0))
            if last_group == assigned:
                self._prev[did] = (assigned, last_steps + 1)
            else:
                self._prev[did] = (assigned, 1)
```