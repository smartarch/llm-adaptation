import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improve drone assignment by considering in-transit drones, avoiding over-protection,
        and biasing toward closest drones for the most threatened fields.
        """
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            # No threat -> idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda fl: fl.threat_level, reverse=True)
        top_field = fields_sorted[0]

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def drone_current_field(d):
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return tid
            return None

        # Current count of drones assigned to each field (counting in-transit and protecting)
        field_current_counts = {}
        for f in fields_sorted:
            fid = f.id
            count = 0
            for d in components:
                if drone_current_field(d) == fid:
                    count += 1
            field_current_counts[fid] = count

        # Group name for top field
        top_group = f"protecting {top_field.id}"

        # Drones required for top protection
        current_top = field_current_counts[top_field.id]
        needed_top = max(0, top_field.drones_for_full_protection - current_top)

        # Build final desired mapping
        desired_group = {d: "idle" for d in components}

        # First, try to fill the top field to full protection using closest available drones.
        if needed_top > 0:
            top_center = field_center(top_field)

            def dist_to_top(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - top_center[0]
                dy = loc.y - top_center[1]
                return math.hypot(dx, dy)

            # Eligible candidates: idle drones or drones from fields that are over-protected
            candidates = []
            # Determine which fields are currently over-protected
            over_protected_fields = set()
            for f in fields_sorted:
                fid = f.id
                if field_current_counts.get(fid, 0) > f.drones_for_full_protection:
                    over_protected_fields.add(fid)

            for d in components:
                cid = drone_current_field(d)
                if cid is None:
                    # Idle
                    candidates.append(d)
                else:
                    if cid in over_protected_fields:
                        # Can reallocate from this field as it's over-protected
                        candidates.append(d)

            candidates.sort(key=dist_to_top)

            to_top = min(needed_top, len(candidates))
            for i in range(to_top):
                d = candidates[i]
                desired_group[d] = top_group

            # Update internal counts to reflect these planned moves
            # This helps subsequent decisions for other fields.
            field_current_counts[top_field.id] += to_top
            # Decrease counts from the old fields if we moved drones away
            # (best-effort: recalculate via current state after reassignment)
            # Note: This is a heuristic; the actual environment will update on the next step.

        # After top is handled (either full or not), allocate for other fields if possible.
        # We'll aim to fully protect as many of the next-threat fields as we can, in threat order.
        for field in fields_sorted[1:]:
            fid = field.id
            target_group = f"protecting {fid}"

            current_for_field = field_current_counts.get(fid, 0)
            needed = max(0, field.drones_for_full_protection - current_for_field)
            if needed == 0:
                continue

            center = field_center(field)

            def dist_to_field(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center[0]
                dy = loc.y - center[1]
                return math.hypot(dx, dy)

            # Eligible candidates:
            # - Idle drones
            # - Drones from fields that are over-protected
            over_protected_fields = set()
            for f2 in fields_sorted:
                fid2 = f2.id
                if field_current_counts.get(fid2, 0) > f2.drones_for_full_protection:
                    over_protected_fields.add(fid2)

            candidates = []
            for d in components:
                cid = drone_current_field(d)
                if cid is None:
                    candidates.append(d)
                else:
                    if cid in over_protected_fields:
                        candidates.append(d)

            candidates.sort(key=dist_to_field)

            assign_count = min(needed, len(candidates))
            for i in range(assign_count):
                d = candidates[i]
                desired_group[d] = target_group
                # Update counts roughly
                old_cid = drone_current_field(d)
                if old_cid is not None:
                    field_current_counts[old_cid] = max(0, field_current_counts.get(old_cid, 0) - 1)
                field_current_counts[fid] = field_current_counts.get(fid, 0) + 1

        # Ensure not too many idle drones: at least half should be protecting if possible
        protecting_drones = sum(1 for d, g in desired_group.items() if g != "idle")
        total_drones = len(components)
        # If we have too few profilings, push a few idle drones to the top field (or next best) to meet the threshold
        if total_drones > 0 and protecting_drones < total_drones // 2:
            deficit = (total_drones // 2) - protecting_drones
            # Collect idle candidates nearest to the top field
            top_center = field_center(top_field)

            def dist_to_top(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - top_center[0]
                dy = loc.y - top_center[1]
                return math.hypot(dx, dy)

            idle_and_close = [d for d in components if desired_group[d] == "idle"]
            idle_and_close.sort(key=dist_to_top)

            for i in range(min(deficit, len(idle_and_close))):
                d = idle_and_close[i]
                desired_group[d] = top_group
                field_current_counts[top_field.id] = field_current_counts.get(top_field.id, 0) + 1
                protecting_drones += 1
                if protecting_drones >= total_drones // 2:
                    break

        # Finally, apply the final group assignments
        for d in components:
            environment.assign_group(d, desired_group.get(d, "idle"))