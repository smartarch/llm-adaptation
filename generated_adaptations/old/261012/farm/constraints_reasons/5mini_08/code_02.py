from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict
from typing import Any

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map of drone identity -> (last_group_id, consecutive_steps)
        # We key by id(component) to handle object identity across steps.
        self._prev = {}

    def _center_of_field(self, field: Any):
        # compute center coordinates of field rectangle
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, lx, ly, rx, ry):
        return math.hypot(lx - rx, ly - ry)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total_drones = len(drones)
        # Build fields with positive threat_level, sorted by descending threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Precompute centers
        field_centers = {f.id: self._center_of_field(f) for f in fields}
        # Helper to form group name
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # Build drone metadata
        drone_meta = []
        for d in drones:
            did = id(d)
            prev_group, prev_steps = self._prev.get(did, (None, 0))
            loc = getattr(d, "location", None)
            lx = getattr(loc, "x", 0.0) if loc is not None else 0.0
            ly = getattr(loc, "y", 0.0) if loc is not None else 0.0
            drone_meta.append({
                "obj": d,
                "id": did,
                "x": lx,
                "y": ly,
                "state": getattr(d, "state", None),
                "target_id": getattr(d, "target_id", None),
                "prev_group": prev_group,
                "prev_steps": prev_steps,
            })

        # We'll produce final assignment mapping drone id -> group
        final_assign = {}

        # Helper: get distance to a field center
        def dist_to_field(dm, field_id):
            cx, cy = field_centers[field_id]
            return self._distance(dm["x"], dm["y"], cx, cy)

        # Helper: get list of available drones (not yet assigned)
        def available_drones():
            return [dm for dm in drone_meta if dm["id"] not in final_assign]

        # Protect fields in order. First, ensure top (most threatened) is fully protected.
        if fields:
            # Top-most threatened field
            top_field = fields[0]
            top_gid = protecting_group(top_field.id)
            required_top = int(getattr(top_field, "drones_for_full_protection", 0))

            # Collect drones that are already assigned to protect that field (based on our prev record or drone current target/state)
            candidates = available_drones()

            # Identify existing protectors from our tracked prev assignments or current drone state/target
            existing_protectors = []
            for dm in candidates:
                # If previously assigned by us to this protecting group, keep
                if dm["prev_group"] == top_gid:
                    existing_protectors.append(dm)
                # Or if drone currently protecting or moving to that target, prefer to keep it
                elif dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == top_field.id:
                    existing_protectors.append(dm)

            # If more existing protectors than required, keep the closest ones among them
            if len(existing_protectors) > required_top:
                existing_protectors.sort(key=lambda dm: dist_to_field(dm, top_field.id))
                existing_protectors = existing_protectors[:required_top]

            # Assign existing protectors first
            for dm in existing_protectors:
                final_assign[dm["id"]] = top_gid

            # Determine how many more needed
            current_count = sum(1 for v in final_assign.values() if v == top_gid)
            need_more = max(0, required_top - current_count)

            if need_more > 0:
                # Choose among remaining drones the closest ones (tie-breaker: prefer ones with shorter prev_steps to reduce breaking long assignments)
                remaining = [dm for dm in available_drones() if dm not in existing_protectors]
                remaining.sort(key=lambda dm: (dist_to_field(dm, top_field.id), dm["prev_steps"]))
                to_take = remaining[:need_more]
                for dm in to_take:
                    final_assign[dm["id"]] = top_gid

        # After top field, try to protect additional fields if needed to meet "at least half drones protecting"
        protected_count = sum(1 for g in final_assign.values() if g != "idle")
        target_protect_count = math.ceil(total_drones / 2.0)  # aim for at least half

        # Iterate other fields (skip first if any)
        for field in fields[1:]:
            if protected_count >= target_protect_count:
                break  # enough protected drones
            gid = protecting_group(field.id)
            required = int(getattr(field, "drones_for_full_protection", 0))
            # If not enough remaining drones to fully protect this field, skip (we prefer full protection)
            remaining_available = len(available_drones())
            if remaining_available < required:
                continue

            # Keep existing protectors for this field if any
            candidates = available_drones()
            existing_protectors = []
            for dm in candidates:
                if dm["prev_group"] == gid:
                    existing_protectors.append(dm)
                elif dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == field.id:
                    existing_protectors.append(dm)

            # Trim existing to required if too many
            if len(existing_protectors) > required:
                existing_protectors.sort(key=lambda dm: dist_to_field(dm, field.id))
                existing_protectors = existing_protectors[:required]

            for dm in existing_protectors:
                final_assign[dm["id"]] = gid

            current_count = sum(1 for v in final_assign.values() if v == gid)
            need_more = max(0, required - current_count)
            if need_more > 0:
                remaining = [dm for dm in available_drones() if dm not in existing_protectors]
                remaining.sort(key=lambda dm: (dist_to_field(dm, field.id), dm["prev_steps"]))
                to_take = remaining[:need_more]
                for dm in to_take:
                    final_assign[dm["id"]] = gid

            protected_count = sum(1 for v in final_assign.values() if v != "idle")

        # Any unassigned drones -> attempt to assign them to other lower-threat fields only if it helps reach target_protect_count
        # (This loop is conservative: it will only assign to full-protect remaining fields if enough drones remain.)
        if protected_count < target_protect_count:
            for field in fields:
                gid = protecting_group(field.id)
                if gid in final_assign.values():
                    continue  # already processed
                required = int(getattr(field, "drones_for_full_protection", 0))
                remaining_available = len(available_drones())
                if remaining_available < required:
                    continue
                # Assign following same logic
                candidates = available_drones()
                # No existing protectors here in this pass, so pick closest
                candidates.sort(key=lambda dm: (dist_to_field(dm, field.id), dm["prev_steps"]))
                to_take = candidates[:required]
                for dm in to_take:
                    final_assign[dm["id"]] = gid
                protected_count = sum(1 for v in final_assign.values() if v != "idle")
                if protected_count >= target_protect_count:
                    break

        # Finally, assign remaining drones to idle
        for dm in available_drones():
            final_assign[dm["id"]] = "idle"

        # Now call environment.assign_group for each drone and update our prev tracking
        for dm in drone_meta:
            d_obj = dm["obj"]
            did = dm["id"]
            assigned_group = final_assign.get(did, "idle")
            # Ensure the assigned group is among provided group_ids. If a protecting group is not valid (field threat might have become 0),
            # fall back to idle
            if assigned_group not in group_ids:
                assigned_group = "idle"
            environment.assign_group(d_obj, assigned_group)

            # Update consecutive counters in self._prev
            last_group, last_steps = self._prev.get(did, (None, 0))
            if last_group == assigned_group:
                self._prev[did] = (assigned_group, last_steps + 1)
            else:
                self._prev[did] = (assigned_group, 1)