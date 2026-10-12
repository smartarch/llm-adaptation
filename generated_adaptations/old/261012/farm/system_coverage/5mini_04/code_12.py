from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0
    TRAVEL_SCALE = 5.0
    TARGET_BONUS = 1.15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(comp, px, py):
            dx = comp.location.x - px
            dy = comp.location.y - py
            return math.hypot(dx, dy)

        def travel_time(comp, px, py):
            return dist(comp, px, py) / max(1e-6, self.DRONE_SPEED)

        def benefit_per_drone(f):
            denom = f.drones_for_full_protection if f.drones_for_full_protection > 0 else 1.0
            return f.threat_level / denom

        # Build list of fields with threat > 0 and valid protecting group
        fields = [f for f in environment.fields if f.threat_level > 0 and f"protecting {f.id}" in group_ids]
        if not fields:
            # nothing to protect
            for comp in components:
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else None)
                environment.assign_group(comp, grp)
            return

        # Choose top field by threat_level (tie-break by id)
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top = fields[0]
        top_grp = f"protecting {top.id}"
        top_req = int(top.drones_for_full_protection)
        top_center = center(top)
        top_benefit = benefit_per_drone(top)

        # Count existing protecting drones per field
        protecting_by_field = {}
        for comp in components:
            if comp.state == "protecting" and getattr(comp, "target_id", None) is not None:
                protecting_by_field.setdefault(comp.target_id, []).append(comp)

        # Lock fields already fully protected by existing protectors
        locked_fields = set()
        for f in fields:
            cur = len(protecting_by_field.get(f.id, []))
            if cur >= int(f.drones_for_full_protection):
                locked_fields.add(f.id)

        assignments = {}

        # 1) Assign locked protecting drones back to their protecting group
        for fid in locked_fields:
            grp = f"protecting {fid}"
            for comp in protecting_by_field.get(fid, []):
                assignments[comp] = grp

        # 2) Preserve drones already protecting or moving_to the top field (they help fulfill top quickly)
        preserved_top = []
        for comp in components:
            if getattr(comp, "target_id", None) == top.id and comp.state in ("protecting", "moving_to_field"):
                if comp not in assignments:
                    assignments[comp] = top_grp
                    preserved_top.append(comp)

        num_preserved_top = sum(1 for c in assignments if assignments[c] == top_grp)
        need_top = max(0, top_req - num_preserved_top)

        # Pools
        def not_assigned():
            return [c for c in components if c not in assignments]

        # 3) Fill top from nearest available non-protecting drones first
        if need_top > 0:
            non_protecting_pool = [c for c in not_assigned() if c.state != "protecting"]
            non_protecting_pool.sort(key=lambda c: (travel_time(c, top_center[0], top_center[1]), c.location.x, c.location.y))
            take = non_protecting_pool[:need_top]
            for c in take:
                assignments[c] = top_grp
            need_top -= len(take)

        # 4) If still need for top, consider reassigning protecting drones from non-locked fields with lower benefit than top
        if need_top > 0:
            protect_candidates = []
            for comp in not_assigned():
                if comp.state == "protecting" and getattr(comp, "target_id", None) is not None:
                    src = comp.target_id
                    if src in locked_fields:
                        continue
                    src_field = next((f for f in fields if f.id == src), None)
                    if src_field is None:
                        continue
                    src_ben = benefit_per_drone(src_field)
                    if src_ben < top_benefit:
                        # prefer lower source benefit and closer to top
                        t = travel_time(comp, top_center[0], top_center[1])
                        protect_candidates.append((src_ben, t, comp, src_field))
            protect_candidates.sort(key=lambda x: (x[0], x[1], str(getattr(x[2], "target_id", ""))))
            for _, _, comp, src_field in protect_candidates:
                if need_top <= 0:
                    break
                assignments[comp] = top_grp
                # this increases remaining need for the source field
                need_top -= 1

        # 5) Compute remaining need per field (accounting for assignments + locked protectors kept)
        remaining_need = {}
        for f in fields:
            grp = f"protecting {f.id}"
            assigned_here = sum(1 for c, g in assignments.items() if g == grp)
            existing_locked = 0
            if f.id in locked_fields:
                existing_locked = len([c for c in protecting_by_field.get(f.id, []) if c in assignments and assignments[c] == grp])
                # locked protectors already assigned above
            # count protecting drones that were not moved (they may be in protecting_by_field but not in assignments)
            existing_protectors_unassigned = [c for c in protecting_by_field.get(f.id, []) if c not in assignments]
            assigned_here += len(existing_protectors_unassigned)
            req = int(f.drones_for_full_protection)
            remaining_need[f.id] = max(0, req - assigned_here)

        # 6) Greedy per-drone allocation for remaining drones: assign each remaining drone to field maximizing marginal score
        available = [c for c in components if c not in assignments]
        # Precompute centers
        centers = {f.id: center(f) for f in fields}
        fields_by_id = {f.id: f for f in fields}

        def marginal_score(comp, f):
            px, py = centers[f.id]
            t = travel_time(comp, px, py)
            base = benefit_per_drone(f)
            score = base / (1.0 + t / self.TRAVEL_SCALE)
            if getattr(comp, "target_id", None) == f.id:
                score *= self.TARGET_BONUS
            # prefer fields that still need drones
            if remaining_need.get(f.id, 0) > 0:
                score *= 1.2
            # deprioritize locked fields that already had enough (they won't be touched)
            if f.id in locked_fields:
                score *= 0.5
            return score

        # Iterate over available drones, each time pick best field for that drone
        while available:
            best = None  # (score, comp, field)
            for comp in available:
                best_field = None
                best_score = 0.0
                for f in fields:
                    # skip fields whose group not in group_ids (already filtered) and skip locked if fully satisfied
                    # locked fields already have remaining_need == 0 by construction
                    s = marginal_score(comp, f)
                    if best_field is None or s > best_score:
                        best_field = f
                        best_score = s
                if best_field is not None:
                    if best is None or best_score > best[0]:
                        best = (best_score, comp, best_field)
            if best is None or best[0] <= 0:
                break
            _, comp, f = best
            grp = f"protecting {f.id}"
            assignments[comp] = grp
            # update remaining_need (but allow oversubscription)
            if remaining_need.get(f.id, 0) > 0:
                remaining_need[f.id] -= 1
            available.remove(comp)

        # 7) Finally, any component still unassigned -> idle (or fallback)
        for comp in components:
            if comp not in assignments:
                assignments[comp] = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else None)

        # 8) Apply assignments, validating group existence
        for comp, grp in assignments.items():
            if grp not in group_ids:
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else grp)
            environment.assign_group(comp, grp)