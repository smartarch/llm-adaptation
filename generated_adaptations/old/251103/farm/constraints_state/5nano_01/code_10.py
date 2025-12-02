import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0), sorted by threat
        fields = getattr(environment, "fields", []) or []
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0.0) > 0.0]
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        # If no threats, idle everyone
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        final_group = {}
        assigned = set()

        # Step 1: Top (most threatened) field
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Current protectors for top field
        current_top = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id]

        # If extras currently protecting top, demote extras to preserve stability
        if len(current_top) > required_top:
            for idx, d in enumerate(current_top):
                if idx < required_top:
                    final_group[d] = top_group
                    assigned.add(d)
                else:
                    # Demote extras to their current field if possible, else idle
                    if getattr(d, "target_id", None) is not None:
                        final_group[d] = f"protecting {d.target_id}"
                    else:
                        final_group[d] = "idle"
                    assigned.add(d)
        else:
            # Keep existing protectors on top
            for d in current_top:
                final_group[d] = top_group
                assigned.add(d)

            need_top = max(0, required_top - len(current_top))
            if need_top > 0:
                # Center of the top field
                cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
                cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

                candidates = []
                for d in components:
                    if d in assigned:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = (dx * dx + dy * dy) ** 0.5
                    st = getattr(d, "state", "")
                    # Priority: prefer drones already moving toward top, then idle, then others
                    if st == "moving_to_field" and getattr(d, "target_id", None) == top_field.id:
                        pr = 0
                    elif st == "idle":
                        pr = 1
                    elif st == "moving_to_field":
                        pr = 2
                    else:
                        pr = 3  # protecting other fields
                    candidates.append((pr, dist, d))

                candidates.sort(key=lambda t: (t[0], t[1]))
                take = min(need_top, len(candidates))
                for i in range(take):
                    d = candidates[i][2]
                    final_group[d] = top_group
                    assigned.add(d)

        # Step 2: Optional secondary field(s)
        if len(threatened_fields) > 1:
            second_field = threatened_fields[1]
            second_group = f"protecting {second_field.id}"
            required_second = int(getattr(second_field, "drones_for_full_protection", 0))

            current_second = [
                d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == second_field.id
            ]
            # Keep current second-field protectors
            for d in current_second:
                if d not in final_group:
                    final_group[d] = second_group
                    assigned.add(d)

            need_second = max(0, required_second - len(current_second))
            if need_second > 0:
                cx2 = (getattr(second_field, "left", 0) + getattr(second_field, "right", 0)) / 2.0
                cy2 = (getattr(second_field, "top", 0) + getattr(second_field, "bottom", 0)) / 2.0

                candidates2 = []
                for d in components:
                    if d in assigned:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - cx2
                        dy = getattr(loc, "y", 0.0) - cy2
                        dist = (dx * dx + dy * dy) ** 0.5
                    st = getattr(d, "state", "")
                    pr = 0 if st == "idle" else (1 if st == "moving_to_field" else 2)
                    if st == "protecting" and getattr(d, "target_id", None) not in (second_field.id, None):
                        pr += 1  # discourage churn from other protected fields
                    candidates2.append((pr, dist, d))

                candidates2.sort(key=lambda t: (t[0], t[1]))
                take2 = min(need_second, len(candidates2))
                for i in range(take2):
                    d = candidates2[i][2]
                    final_group[d] = second_group
                    assigned.add(d)

        # Step 3: Assign remaining drones
        threatened_ids = {f.id for f in threatened_fields}
        for d in components:
            if d in assigned:
                continue
            # If drone is protecting some threatened field, keep it protecting that field
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if st == "protecting" and tid in threatened_ids:
                final_group[d] = f"protecting {tid}"
            else:
                # Otherwise idle or, if there are any remaining drones and there are still threatened fields,
                # allow some to join top/second if not already full. Here we treat as idle to avoid churn.
                final_group[d] = "idle"

        # Apply assignments (one per drone)
        for d in components:
            environment.assign_group(d, final_group[d])