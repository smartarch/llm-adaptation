# Reasoning and strategy (embedded as code comments):
# Goal: further reduce average damage by aggressively and safely distributing drones
# to fully protect as many high-threat fields as possible in each step.
# Key ideas:
# - Treat every field with positive threat as a potential target to fully protect.
# - Use inbound drones (arriving_drones) and drones already protecting/moving_to_field toward a field
#   when computing how many more are needed for full protection.
# - Sort fields by (threat_level, deficit) so that we prioritize the most dangerous fields that are
#   most in need of protection.
# - Allocate the closest available drones to fill each field's protection gap, in that priority order.
# - Do not evict drones from a field once it becomes fully protected; otherwise reallocate in priority order.
# - If there are not enough drones to fully protect all fields, at least ensure the highest-priority fields are protected.
# - Keep the remaining drones idle.

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 0) Gather fields with positive threat levels
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Helper: compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # 1) Build a per-field view: threat, required, current, inbound
        field_infos = []
        for f in fields:
            cx, cy = center_of(f)
            # Drones currently targeting this field (protecting or en route)
            current_for_field = []
            for idx, d in enumerate(components):
                if getattr(d, "target_id", None) == f.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                    current_for_field.append(idx)

            current_count = len(current_for_field)
            inbound = getattr(f, "arriving_drones", 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            total_present = current_count + inbound
            deficit = max(0, required - total_present)

            field_infos.append({
                "field": f,
                "threat": getattr(f, "threat_level", 0),
                "current_protecting": current_for_field,
                "inbound": inbound,
                "required": required,
                "deficit": deficit,
            })

        # If nothing can be defended (deficit==0 for all), idle all
        if not field_infos:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by priority: highest threat first, then larger deficit
        field_infos.sort(key=lambda info: (-info["threat"], -info["deficit"]))

        # 3) Assign drones to fields in priority order
        assigned_indices = set()

        for info in field_infos:
            f = info["field"]
            g_name = f"protecting {f.id}"
            if g_name not in group_ids:
                continue

            # Current drones for this field (protecting or en route)
            current_for_field = info["current_protecting"]
            # Ensure they are in the correct group
            for idx in current_for_field:
                environment.assign_group(components[idx], g_name)
            assigned_indices.update(current_for_field)

            # Update count including inbound toward this field
            inbound = info["inbound"]
            current_count = len(current_for_field)
            effective_count = current_count + inbound
            needed = max(0, int(info["required"]) - effective_count)

            if needed <= 0:
                continue

            # Choose closest available drones to fill the gap
            cx, cy = center_of(f)
            candidates = []
            for idx, d in enumerate(components):
                if idx in assigned_indices:
                    continue
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, idx))
            candidates.sort()
            for i in range(min(needed, len(candidates))):
                idx = candidates[i][1]
                environment.assign_group(components[idx], g_name)
                assigned_indices.add(idx)

        # 4) Remaining drones go idle
        for idx, d in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(d, "idle")