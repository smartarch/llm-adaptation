Reasoning and improved adaptation strategy

What I changed and why

- Previous versions sometimes pulled protecting drones away from other fields, which can backfire by turning multiple partially-protected fields into fully-unprotected ones. To reduce total damage we should avoid breaking existing protections unless the benefit clearly outweighs the cost.
- I now treat currently protecting drones as "reserved" for their fields. Moving-to-field drones are treated as committed as well, but they are more flexible than protecting drones.
- When protecting the highest-threat field we:
  1. Use its already-committed drones (protecting + moving to it).
  2. Add idle drones closest to that field.
  3. If still short, steal only "extra" committed drones from other fields — that is, those fields that already have more committed drones than necessary for full protection. We prefer stealing moving_to_field drones first (less disruptive), then protecting drones that are extras.
  4. As a last resort, we may take drones from lower-threat fields if necessary to secure the top field, but we prefer to keep protections intact.
- After securing the top field, we try to fully protect as many other fields as possible using the same priority (their committed drones + idle + steal extras), processing fields in descending threat order. This attempts to maximize the number of fully protected high-threat fields while minimizing destructive reassignment.
- Drones left after these allocations are assigned to an idle group.
- We always account for travel time (distance / speed) when choosing idle or stealable drones so closer drones are prioritized.
- Every drone is explicitly assigned a group every call.

This heuristic tries to preserve beneficial current allocations while still being efficient about reusing idle resources and only reassigning committed drones when that won't harm overall protection (or is necessary for the top-priority field). It should reduce unnecessary churn and reduce total damage.

Code

```py
from typing import List, Dict, Set
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Heuristic strategy:
        - Reserve currently protecting drones for their fields (least reassignable).
        - Treat moving_to_field drones as committed but more flexible.
        - Protect the highest-threat field first:
            use committed to that field, then nearest idle drones, then steal 'extra' committed drones
            from other fields (first moving_to_field extras, then protecting extras). Only steal from
            lower-threat fields as last resort.
        - After the top field is secured, attempt to fully protect other fields (by threat descending)
          using the same priority rules.
        - Any remaining drones -> idle.
        """
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(drone, cx, cy):
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return math.hypot(dx, dy)

        SPEED = 2.0
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Precompute centers
        centers = {f.id: center(f) for f in threatened}
        # Map comps to lists by state and target
        protecting_by_field: Dict[str, List] = {}
        moving_by_field: Dict[str, List] = {}
        idle_drones: List = []
        # Also keep list of all comps
        all_comps = list(components)

        for comp in all_comps:
            st = getattr(comp, "state", "")
            tid = getattr(comp, "target_id", None)
            if st == "protecting" and tid is not None:
                protecting_by_field.setdefault(tid, []).append(comp)
            elif st == "moving_to_field" and tid is not None:
                moving_by_field.setdefault(tid, []).append(comp)
            else:
                # treat as idle / uncommitted
                idle_drones.append(comp)

        # For deterministic behavior, sort threatened fields by threat and id when needed
        threatened_sorted = sorted(threatened, key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")), reverse=True)

        # Compute required and committed counts
        field_info = {}
        for f in threatened:
            pid = f.id
            protecting = list(protecting_by_field.get(pid, []))
            moving = list(moving_by_field.get(pid, []))
            required = int(getattr(f, "drones_for_full_protection", 0))
            committed_count = len(protecting) + len(moving)
            field_info[pid] = {
                "field": f,
                "required": required,
                "protecting": protecting,
                "moving": moving,
                "committed": committed_count,
                "threat": getattr(f, "threat_level", 0),
            }

        # Identify top field
        top_field = threatened_sorted[0]
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # cannot protect top; fallback all idle
            for comp in all_comps:
                environment.assign_group(comp, fallback_group)
            return

        # Helper to pick nearest drones from a pool to a field (returns chosen list)
        def pick_nearest(pool: List, fid: str, k: int) -> List:
            if k <= 0 or not pool:
                return []
            cx, cy = centers[fid]
            # sort by travel time (distance / SPEED)
            return sorted(pool, key=lambda d: distance(d, cx, cy) / SPEED)[:k]

        # Build initial selections: reserved = protecting drones (we will not steal these unless they are extras)
        selected_for_field: Dict[str, List] = {}
        assigned = set()  # drones assigned to protecting groups

        # Initialize with committed drones staying where they are (protecting + moving)
        for fid, info in field_info.items():
            # Initially keep both protecting and moving as committed (we'll allow stealing from extras later)
            committed_list = list(info["protecting"]) + list(info["moving"])
            selected_for_field[fid] = list(committed_list)

        # Track current available idle pool (drones not yet assigned)
        # We haven't yet marked any drone as assigned; reserved drones are considered reserved but may still be stolen if extras
        idle_pool = list(idle_drones)

        # Compute extras (how many committed above required) per field
        def compute_extras():
            extras = {}
            for fid, info in field_info.items():
                required = info["required"]
                committed = len(selected_for_field.get(fid, []))
                extras[fid] = max(0, committed - required)
            return extras

        extras = compute_extras()

        # Function to steal up to 'count' drones from fields that have extras.
        # Preference: moving drones first (less disruption), then protecting extras.
        def steal_from_extras(count: int, prefer_lower_threat_than=None) -> List:
            stolen = []
            if count <= 0:
                return stolen
            # Build list of candidate fields that have extras
            # We prefer stealing from fields with lower threat if prefer_lower_threat_than specified
            candidates = []
            for fid, ex in extras.items():
                if ex <= 0:
                    continue
                # optional constraint: only consider if field threat < prefer_lower_threat_than
                if prefer_lower_threat_than is not None and field_info[fid]["threat"] >= prefer_lower_threat_than:
                    continue
                candidates.append(fid)
            # Sort candidates by (extra desc, low threat first) to steal from less-important fields with many extras
            candidates.sort(key=lambda fid: (extras[fid], -field_info[fid]["threat"]), reverse=False)
            for fid in candidates:
                if len(stolen) >= count:
                    break
                # gather stealable drones: moving first, then protecting
                movers = [d for d in selected_for_field[fid] if d in moving_by_field.get(fid, [])]
                protectors = [d for d in selected_for_field[fid] if d in protecting_by_field.get(fid, [])]
                # Try movers first
                while movers and extras[fid] > 0 and len(stolen) < count:
                    d = movers.pop(0)
                    selected_for_field[fid].remove(d)
                    stolen.append(d)
                    extras[fid] -= 1
                # Then protectors if still extras
                while protectors and extras[fid] > 0 and len(stolen) < count:
                    d = protectors.pop(0)
                    selected_for_field[fid].remove(d)
                    stolen.append(d)
                    extras[fid] -= 1
            return stolen

        # --- Stage 1: ensure top field is fully protected ---
        top_required = field_info[top_id]["required"]
        top_selected = selected_for_field[top_id]
        needed_top = max(0, top_required - len(top_selected))

        # Use idle drones first (closest)
        if needed_top > 0 and idle_pool:
            choose = pick_nearest(idle_pool, top_id, needed_top)
            for d in choose:
                top_selected.append(d)
                idle_pool.remove(d)
            needed_top = max(0, top_required - len(top_selected))

        # If still needed, steal extras from other fields that have extras (prefer lower-threat fields)
        if needed_top > 0:
            # prefer stealing from fields with threat lower than top_field.threat
            stolen = steal_from_extras(needed_top, prefer_lower_threat_than=field_info[top_id]["threat"])
            # If insufficient, allow stealing from any extras regardless of threat
            if len(stolen) < needed_top:
                stolen2 = steal_from_extras(needed_top - len(stolen), prefer_lower_threat_than=None)
                stolen.extend(stolen2)
            # If any stolen, add to top_selected
            for d in stolen:
                top_selected.append(d)
            needed_top = max(0, top_required - len(top_selected))

        # As a last resort (should be rare), steal from lower-threat fields even if it causes them to fall short:
        # find candidate fields with lower threat and take the least-critical drone (moving first then protecting),
        # but we only do this if it's necessary to secure the top field (we assume top must be protected).
        if needed_top > 0:
            # build list of candidate drones from other fields that are not in extras (we will cause deficit)
            candidates = []
            for fid, info in field_info.items():
                if fid == top_id:
                    continue
                if info["threat"] >= field_info[top_id]["threat"]:
                    # prefer not to steal from fields with equal/higher threat
                    continue
                # collect moving and protecting drones
                for d in info["moving"]:
                    if d not in top_selected:
                        candidates.append((fid, d, distance(d, *centers[top_id]) / SPEED))
                for d in info["protecting"]:
                    if d not in top_selected:
                        candidates.append((fid, d, distance(d, *centers[top_id]) / SPEED))
            # sort candidates by travel time ascending
            candidates.sort(key=lambda t: t[2])
            for fid, d, _ in candidates:
                if needed_top <= 0:
                    break
                # remove d from its field selection
                if d in selected_for_field[fid]:
                    selected_for_field[fid].remove(d)
                top_selected.append(d)
                needed_top -= 1
            # recompute extras after forced steals
            extras = compute_extras()

        # Mark drones assigned to top for later
        assigned_top = set(selected_for_field[top_id])

        # Remove assigned top drones from idle_pool if present
        idle_pool = [d for d in idle_pool if d not in assigned_top]

        # Recompute extras after top allocation
        extras = compute_extras()

        # --- Stage 2: try to fully protect other fields in descending threat order ---
        # We'll attempt to fully protect each remaining field using:
        # their committed drones (already in selected_for_field), idle_pool (closest), then steal extras.
        for f in threatened_sorted:
            fid = f.id
            if fid == top_id:
                continue
            info = field_info[fid]
            req = info["required"]
            currently_selected = selected_for_field.get(fid, [])
            need = max(0, req - len(currently_selected))
            if need <= 0:
                # already satisfied
                continue
            # Use idle drones first
            if idle_pool:
                take = pick_nearest(idle_pool, fid, need)
                for d in take:
                    selected_for_field[fid].append(d)
                    idle_pool.remove(d)
                need = max(0, req - len(selected_for_field[fid]))
            # If still need, steal extras (prefer from even lower-threat fields)
            if need > 0:
                stolen = steal_from_extras(need, prefer_lower_threat_than=info["threat"])
                # if insufficient, allow stealing from any extras
                if len(stolen) < need:
                    stolen2 = steal_from_extras(need - len(stolen), prefer_lower_threat_than=None)
                    stolen.extend(stolen2)
                for d in stolen:
                    selected_for_field[fid].append(d)
                need = max(0, req - len(selected_for_field[fid]))
            # If still need, we do not forcibly break other fields here (better to leave partial), so move on.

            # update extras after each allocation
            extras = compute_extras()

        # After all attempts, assign groups:
        drone_to_group: Dict = {}
        # Assign those in selected_for_field to corresponding protecting groups
        for fid, drones in selected_for_field.items():
            group_name = f"protecting {fid}"
            if group_name not in group_ids:
                # skip if this group name not valid; drones will default to idle later
                continue
            for d in drones:
                # do not overwrite if drone already assigned (shouldn't happen)
                if d in drone_to_group:
                    continue
                drone_to_group[d] = group_name

        # Any drone not assigned -> idle
        for comp in all_comps:
            grp = drone_to_group.get(comp, fallback_group)
            environment.assign_group(comp, grp)
```