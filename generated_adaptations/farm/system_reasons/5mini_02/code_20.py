from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Greedy, value-per-drone allocation strategy:
    - Always fully protect the single most threatened field.
    - Then greedily fully protect other fields ordered by (threat_level / drones_for_full_protection).
    - Prefer drones already protecting or moving to a field; use distance as tiebreaker.
    - Do not overprotect a field. If not enough drones to fully protect a field, skip it (favor fully protecting fewer fields).
    - Try to ensure at least half the drones are protecting by filling remaining free slots (without overprotection).
    """

    def assign_drones(self, components, environment, group_ids, step: int):
        # basic helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def euclid(a, b):
            return math.hypot(a.x - b[0], a.y - b[1])

        # idle fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # collect fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # no threats -> idle all drones
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # precompute centers and lookup
        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        # primary: highest threat_level (must be fully protected)
        primary = max(fields, key=lambda f: f.threat_level)

        # build priority list: primary first, then other fields sorted by value-per-drone
        others = [f for f in fields if f.id != primary.id]
        # avoid division by zero
        def value_per_drone(f):
            cap = max(1, getattr(f, "drones_for_full_protection", 0))
            return getattr(f, "threat_level", 0) / cap
        others.sort(key=value_per_drone, reverse=True)
        ordered_fields = [primary] + others

        total_drones = len(components)
        min_protectors = (total_drones + 1) // 2  # ceil half

        # selection key for choosing best drones for a field:
        # prefer (in order): protecting with same target, moving_to_field with same target, idle, then others; tiebreak by distance
        def select_key(drone, field):
            st = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)
            # rank: lower is better
            if st == "protecting" and tid == field.id:
                rank = 0
            elif st == "moving_to_field" and tid == field.id:
                rank = 1
            elif st == "idle":
                rank = 2
            else:
                rank = 3
            d = euclid(drone.location, centers[field.id])
            return (rank, d)

        # assignment structures
        assignments = {}
        unassigned = set(components)

        # helper to get valid group name (fallback to idle if not present)
        def protecting_group_name(field):
            g = f"protecting {field.id}"
            return g if g in group_ids else idle_group

        # 1) Greedily fully protect fields in priority order, but only if we can supply the full required number
        for f in ordered_fields:
            cap = getattr(f, "drones_for_full_protection", 0)
            if cap <= 0:
                continue
            # choose best candidates from unassigned
            candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))
            if len(candidates) < cap:
                # skip partial protection here; prefer fully protecting other fields
                continue
            chosen = candidates[:cap]
            grp = protecting_group_name(f)
            for d in chosen:
                assignments[d] = grp
                unassigned.remove(d)

        # 2) After full-protection pass, ensure at least half drones are protecting if possible
        def protecting_count(assign_map):
            return sum(1 for g in assign_map.values() if isinstance(g, str) and g.startswith("protecting "))

        prot_count = protecting_count(assignments)

        if prot_count < min_protectors:
            need_more = min_protectors - prot_count
            # Fill free slots in fields (without overprotecting), ordered by value-per-drone (use ordered_fields)
            for f in ordered_fields:
                if need_more <= 0 or not unassigned:
                    break
                cap = getattr(f, "drones_for_full_protection", 0)
                if cap <= 0:
                    continue
                grp = protecting_group_name(f)
                already = sum(1 for d, g in assignments.items() if g == grp)
                free_slots = max(0, cap - already)
                if free_slots <= 0:
                    continue
                take = min(free_slots, need_more, len(unassigned))
                if take <= 0:
                    continue
                candidates = sorted(list(unassigned), key=lambda d: select_key(d, f))[:take]
                for d in candidates:
                    assignments[d] = grp
                    unassigned.remove(d)
                    need_more -= 1

            # If still need_more and no free slots remain (i.e., all caps filled), we can't reach half without overprotecting; do not overprotect.

        # 3) Remaining drones -> idle
        for d in list(unassigned):
            assignments[d] = idle_group
            unassigned.remove(d)

        # 4) Final enforcement (sanity): ensure no group exceeds cap (trim if necessary)
        # Build map grp -> list of drones
        grp_to_drones = {}
        for d, g in assignments.items():
            grp_to_drones.setdefault(g, []).append(d)
        for f in fields:
            grp = protecting_group_name(f)
            if grp == idle_group:
                continue
            cap = getattr(f, "drones_for_full_protection", 0)
            assigned_list = grp_to_drones.get(grp, [])
            if len(assigned_list) <= cap:
                continue
            # if over, sort assigned_list by suitability and keep best cap
            assigned_list.sort(key=lambda d: select_key(d, f))
            keep = set(assigned_list[:cap])
            for d in assigned_list[cap:]:
                assignments[d] = idle_group

        # 5) Apply assignments for every component
        for d in components:
            grp = assignments.get(d, idle_group)
            # final safety check for group validity
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(d, grp)