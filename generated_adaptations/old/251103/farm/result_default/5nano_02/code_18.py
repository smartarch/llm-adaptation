# Strategy rationale embedded in comments:
# - Goal: Further reduce average damage by improving the drone-to-field assignment.
# - Core approach:
#   1) Phase 1: Guarantee the top-threat field (highest threat_level) is fully protected using the closest movable drones.
#      Movable drones are either idle or currently guarding a field that has slack (i.e., more drones than drones_for_full_protection).
#      This minimizes travel while preserving protection for other fields.
#   2) Phase 2: Global distance-aware greedy matching for remaining protection slots across all threatened fields.
#      Repeatedly assign the best (drone, field) pair by maximizing a score:
#        score = threat_level(field) * (2.0 if this assignment would complete the field's protection else 1.0) / (distance_to_field_center + 1e-9)
#      This emphasizes high-threat fields and completion of protection, while preferring nearby drones.
#   3) Phase 3: Any drone not assigned becomes idle.
# - Rationale: This combines strict top-field protection with a globally optimal-ish distribution that minimizes travel and respects slack, which should yield lower damage in dynamic bird scenarios.

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist2(drone, tx, ty):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", None)
            y = getattr(loc, "y", None)
            if x is None or y is None:
                if isinstance(loc, dict):
                    x = loc.get("x", 0.0)
                    y = loc.get("y", 0.0)
            if x is None or y is None:
                return float("inf")
            dx = x - tx
            dy = y - ty
            return dx * dx + dy * dy

        # Gather threat fields
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Map field_id -> field object
        field_by_id = {f.id: f for f in threat_fields}

        # Top field: highest threat level
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # Current protection counts per field
        counts = {f.id: 0 for f in threat_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in counts:
                    counts[tid] = counts.get(tid, 0) + 1

        # Slack: how many drones can be moved away from a field without breaking full protection
        def field_slack(field_id):
            need = getattr(field_by_id[field_id], "drones_for_full_protection", 0)
            return max(0, counts.get(field_id, 0) - need)

        # Movable predicate: idle or protecting a field with slack > 0
        def is_movable(d):
            st = getattr(d, "state", None)
            if st != "protecting":
                return True
            source = getattr(d, "target_id", None)
            if source is None:
                return True
            return field_slack(source) > 0

        assigned = set()

        # Phase 1: Top field protection (fully protect top_field with closest movable drones)
        top_missing = max(0, getattr(top_field, "drones_for_full_protection", 0) - counts.get(top_field.id, 0))
        tx, ty = field_center(top_field)
        while top_missing > 0:
            movable = [d for d in components if d not in assigned and is_movable(d)]
            if not movable:
                break
            d = min(movable, key=lambda dr: dist2(dr, tx, ty))
            environment.assign_group(d, f"protecting {top_field.id}")
            assigned.add(d)
            old_target = getattr(d, "target_id", None)
            if old_target is not None and old_target != top_field.id:
                counts[old_target] = max(0, counts.get(old_target, 0) - 1)
            counts[top_field.id] = counts.get(top_field.id, 0) + 1
            top_missing -= 1

        # Phase 2: Global distance-aware matching for remaining slots
        def field_need(fid):
            f = field_by_id[fid]
            return max(0, getattr(f, "drones_for_full_protection", 0) - counts.get(fid, 0))

        remaining_fields = [f for f in threat_fields if field_need(f.id) > 0]

        while True:
            movable_drones = [d for d in components if d not in assigned and is_movable(d)]
            if not movable_drones or not remaining_fields:
                break

            best_pair = None
            best_score = -1.0

            for d in movable_drones:
                for f in remaining_fields:
                    need = field_need(f.id)
                    if need <= 0:
                        continue
                    cx, cy = field_center(f)
                    dd = dist2(d, cx, cy)
                    will_complete = (counts.get(f.id, 0) + 1) >= getattr(f, "drones_for_full_protection", 0)
                    score = getattr(f, "threat_level", 0) * (2.0 if will_complete else 1.0) / (dd + 1e-9)
                    if score > best_score:
                        best_score = score
                        best_pair = (d, f)

            if best_pair is None:
                break

            d, f = best_pair
            old = getattr(d, "target_id", None)
            if old is not None and old != f.id:
                counts[old] = max(0, counts.get(old, 0) - 1)
            environment.assign_group(d, f"protecting {f.id}")
            assigned.add(d)
            counts[f.id] = counts.get(f.id, 0) + 1

            # Update remaining_fields
            remaining_fields = [ff for ff in threat_fields if field_need(ff.id) > 0]

        # Phase 3: Remaining drones idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")