Reasoning and adaptation strategy

Brief plan and motivation

- Keep the core rule: always fully protect the single highest-threat field (top field) with the closest drones.
- To reduce unnecessary disruption, pick drones for the top field in this priority order:
  1. Drones already committed to the top (protecting or moving_to_field → cheap and fast).
  2. Idle drones (closest first).
  3. Drones moving to other fields (closest first).
  4. Protecting drones from other fields only if absolutely necessary — prefer stealing from fields that have "extras" (more protectors than required), otherwise from the lowest-threat fields and the closest protectors.
- After the top field is secured, attempt to fully protect additional fields in descending threat order using only available drones that are not protecting other fields (idle and movable). Do not steal protecting drones for these other fields.
- Any remaining drones that were originally protecting some field keep protecting their field (we explicitly reassign them to the same protecting group), and all drones not assigned to a protecting role are placed into the "idle" group.
- Deterministic tie-breaking is used (by id or coordinates) so behavior is stable.

Why this should help
- Enforcing the top-field rule strictly while minimizing protective disruption tends to preserve existing coverage and get the most out of available idle/moving drones.
- Avoiding aggressive stealing of protecting drones prevents turning several partially-protected fields into fully-unprotected ones (which caused worse damage in previous runs).
- Using closest idle and moving drones first reduces travel time so protection becomes effective quicker.

Implementation below follows this strategy. It explicitly assigns every component each step and validates group names against group_ids.

```py
from typing import List, Dict
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Strategy:
        - Fully protect the highest-threat field with the closest drones, using this priority:
          (committed to top) -> idle -> moving_to_field (other targets) -> protecting extras -> other protectors (least preferred).
        - Then greedily fully protect other fields (by threat desc) using available drones (idle and movable), without stealing protecting drones.
        - Explicitly reassign protecting drones to their current protecting groups unless they were stolen for the top field.
        - All other drones go to "idle".
        """
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(a_x, a_y, b_x, b_y):
            return math.hypot(a_x - b_x, a_y - b_y)

        # Groups
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Centers
        centers = {f.id: center(f) for f in threatened}

        # Top field selection (highest threat, tie-break by id)
        top_field = max(threatened, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # cannot protect top (no valid group) -> idle all
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))

        # Partition drones by state/target and compute distances
        protecting_by_field: Dict[str, List] = {}
        moving_by_field: Dict[str, List] = {}
        idle_drones = []
        all_comps = list(components)

        for comp in all_comps:
            st = getattr(comp, "state", "")
            tid = getattr(comp, "target_id", None)
            if st == "protecting" and tid is not None:
                protecting_by_field.setdefault(tid, []).append(comp)
            elif st == "moving_to_field" and tid is not None:
                moving_by_field.setdefault(tid, []).append(comp)
            else:
                idle_drones.append(comp)

        # helper distance to a field
        def dist_to_field(d, fid):
            cx, cy = centers[fid]
            return dist(d.location.x, d.location.y, cx, cy)

        # 1) Select drones for top field using priority rules

        selected_top = []
        selected_top_set = set()

        # (a) committed to top (protecting or moving)
        committed_top = []
        committed_top.extend(protecting_by_field.get(top_id, []))
        committed_top.extend(moving_by_field.get(top_id, []))
        # deterministic order: protecting first then moving, each sorted by coordinates
        def coord_key(d):
            return (d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or "")
        committed_top = sorted(set(committed_top), key=coord_key)
        for d in committed_top:
            if len(selected_top) >= top_required:
                break
            selected_top.append(d)
            selected_top_set.add(d)

        # (b) idle drones closest
        if len(selected_top) < top_required and idle_drones:
            idle_candidates = [d for d in idle_drones if d not in selected_top_set]
            idle_candidates.sort(key=lambda d: (dist_to_field(d, top_id), coord_key(d)))
            for d in idle_candidates:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (c) moving_to_field drones targeting other fields (closest)
        if len(selected_top) < top_required:
            movers_other = []
            for fid, movs in moving_by_field.items():
                if fid == top_id:
                    continue
                for d in movs:
                    if d not in selected_top_set:
                        movers_other.append(d)
            movers_other.sort(key=lambda d: (dist_to_field(d, top_id), coord_key(d)))
            for d in movers_other:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (d) protecting extras from other fields (protectors beyond their required)
        if len(selected_top) < top_required:
            # determine extras
            extras = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                required = int(getattr(next((f for f in environment.fields if f.id == fid), None), "drones_for_full_protection", 0))
                extra_count = max(0, len(prots) - required)
                if extra_count > 0:
                    # choose protectors sorted by proximity to top
                    for d in sorted(prots, key=lambda d: (dist_to_field(d, top_id), coord_key(d))):
                        if extra_count <= 0:
                            break
                        if d in selected_top_set:
                            continue
                        extras.append(d)
                        extra_count -= 1
            for d in extras:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (e) if still short, steal protecting drones from other fields (least harmful: lowest-threat fields first, and closest)
        if len(selected_top) < top_required:
            # build list of protecting drones not yet considered, grouped by their field's threat
            protect_candidates = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                # field threat
                field_threat = getattr(next((f for f in environment.fields if f.id == fid), None), "threat_level", 0)
                for d in prots:
                    if d in selected_top_set:
                        continue
                    protect_candidates.append((field_threat, dist_to_field(d, top_id), fid, d))
            # sort by lowest threat first, then closest distance
            protect_candidates.sort(key=lambda t: (t[0], t[1], coord_key(t[3])))
            for _, _, _, d in protect_candidates:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # Now selected_top holds up to required_top drones (maybe fewer if not enough)
        # 2) Prepare initial mapping: default everyone -> idle, but protecting/moving keep their current target unless we override
        drone_to_group: Dict[object, str] = {}
        # start with idle default
        for comp in all_comps:
            drone_to_group[comp] = fallback_group

        # assign existing protecting drones to their protecting groups (unless they've been chosen for top — those will be overridden)
        for fid, prots in protecting_by_field.items():
            grp_name = f"protecting {fid}"
            if grp_name not in group_ids:
                continue
            for d in prots:
                # if this protector was stolen for top, we'll override below
                if d not in selected_top_set:
                    drone_to_group[d] = grp_name

        # assign existing moving_to_field drones to their target group if valid (unless they were chosen for top)
        for fid, movs in moving_by_field.items():
            grp_name = f"protecting {fid}"
            if grp_name not in group_ids:
                continue
            for d in movs:
                if d not in selected_top_set and drone_to_group.get(d, fallback_group) == fallback_group:
                    # only set if not already set (protectors already set above)
                    drone_to_group[d] = grp_name

        # idle drones remain fallback unless assigned below

        # Now override mapping for top-selected drones
        for d in selected_top:
            drone_to_group[d] = top_group

        # Track which drones are still available for assigning to other fields (not assigned to top, and not protecting others)
        assigned_set = set(d for d, g in drone_to_group.items() if g.startswith("protecting "))
        # Build pools:
        available = [d for d in all_comps if d not in assigned_set]  # candidates we can assign to new protections
        # Note: available includes idle drones and moving_to_field not assigned to their own target (they will be reassigned), as well as protectors that were stolen for top (already assigned to top, so not in available)

        # 3) Greedily fully protect other fields in descending threat order using available drones and committed moving_to_field for that field
        other_fields = sorted([f for f in threatened if f.id != top_id], key=lambda f: (f.threat_level, getattr(f, "id", "")), reverse=True)
        for f in other_fields:
            fid = f.id
            grp_name = f"protecting {fid}"
            if grp_name not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            # compute currently committed (protecting and moving targeting this field) that are not stolen (i.e., whose current mapping is to this field)
            committed = []
            # prefer currently protecting then moving
            for d in protecting_by_field.get(fid, []):
                if drone_to_group.get(d) == grp_name:
                    committed.append(d)
            for d in moving_by_field.get(fid, []):
                if drone_to_group.get(d) == grp_name:
                    # include moving that we left in place
                    committed.append(d)
            if len(committed) >= required:
                # nothing to do; they are already assigned (we keep them)
                continue
            needed = required - len(committed)
            # choose closest available drones to this field
            candidates = [d for d in available if d not in selected_top_set]
            if not candidates:
                continue
            candidates.sort(key=lambda d: (dist_to_field(d, fid), d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or ""))
            chosen = []
            for d in candidates:
                if len(chosen) >= needed:
                    break
                chosen.append(d)
            # assign chosen to this group's protecting role
            for d in chosen:
                drone_to_group[d] = grp_name
                if d in available:
                    available.remove(d)
            # done for this field

        # 4) Ensure any protecting drones that we did not steal are still assigned (already set above). Any remaining drones in 'available' remain idle.
        # Final: assign group for every drone explicitly
        for comp in all_comps:
            grp = drone_to_group.get(comp, fallback_group)
            environment.assign_group(comp, grp)