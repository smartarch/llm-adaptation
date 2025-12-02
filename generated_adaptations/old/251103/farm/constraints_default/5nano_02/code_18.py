# Strategy rationale (embedded as comments for traceability)
# - Goal: Always fully protect the most threatened field using the closest drones.
# - Drones that are currently protecting a field are preferred to stay on that field if its threat remains high.
# - If additional drones are needed to reach full protection for the top field, assign the closest available drones.
# - The top field protection must use a valid group name. If the exact "protecting {field_id}" group
#   is not available, attempt a robust match against other "protecting ..." groups that refer to the same field.
# - If no valid protection group can be found for the top field, or after reassignment the top field cannot be protected,
#   fall back to idle to avoid invalid assignments.
# - Ensure every drone is assigned to exactly one valid group in this step.

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

        def dist2(drone, x, y):
            dx = getattr(drone.location, "x", 0.0) - x
            dy = getattr(drone.location, "y", 0.0) - y
            return dx * dx + dy * dy

        def id_norm(s):
            return "".join(ch.lower() for ch in str(s) if ch.isalnum())

        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat_level desc, deterministically by id
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "id", "")),
            reverse=True,
        )

        top_field = threat_fields_sorted[0]
        top_field_id = getattr(top_field, "id", None)
        top_center_x, top_center_y = field_center(top_field)

        # Current drones protecting the top field
        current_top_protecting = [
            d for d in components
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field_id
        ]

        drones_for_top = getattr(top_field, "drones_for_full_protection", 0)
        try:
            need_top = max(0, int(drones_for_top) - int(len(current_top_protecting)))
        except Exception:
            need_top = 0

        # Resolve a robust protection group for the top field
        preferred_group = f"protecting {top_field_id}"
        group_ids_set = set(group_ids if group_ids is not None else [])
        top_group = None
        top_group_valid = False

        if preferred_group in group_ids_set:
            top_group = preferred_group
            top_group_valid = True
        else:
            # Robust matching: try exact suffix, normalized forms, or containment
            best_match = None
            nf_top = id_norm(top_field_id)
            for g in (group_ids or []):
                if not isinstance(g, str) or not g.startswith("protecting "):
                    continue
                suffix = g[len("protecting "):]
                if suffix.strip() == str(top_field_id).strip():
                    best_match = g
                    break
                nf_suffix = id_norm(suffix)
                if nf_suffix == nf_top:
                    best_match = g
                    break
                # Additional heuristic: if normalized forms share a common substring
                if nf_top in nf_suffix or nf_suffix in nf_top:
                    best_match = g
                    break
            if best_match:
                top_group = best_match
                top_group_valid = top_group in group_ids_set

        # Build the set of drones that will protect the top field
        top_protecting = list(current_top_protecting)

        if need_top > 0:
            # Pick the closest drones not already protecting the top field
            not_current = [d for d in components if d not in top_protecting]
            not_current.sort(key=lambda d: dist2(d, top_center_x, top_center_y))
            for d in not_current[:need_top]:
                top_protecting.append(d)

        # Assign groups for all drones
        for d in components:
            if d in top_protecting:
                if top_group_valid and top_group is not None:
                    environment.assign_group(d, top_group)
                else:
                    # If no valid top-group available, idle to avoid invalid assignments
                    environment.assign_group(d, "idle")
            else:
                # If drone is currently protecting some field, try to keep it if that field is still threatened
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                    tgt_id = d.target_id
                    tgt_field = next((f for f in fields if getattr(f, "id", None) == tgt_id), None)
                    if tgt_field is not None and getattr(tgt_field, "threat_level", 0) > 0:
                        tgt_group = f"protecting {tgt_id}"
                        if tgt_group in group_ids_set:
                            environment.assign_group(d, tgt_group)
                        else:
                            environment.assign_group(d, "idle")
                    else:
                        environment.assign_group(d, "idle")
                else:
                    environment.assign_group(d, "idle")