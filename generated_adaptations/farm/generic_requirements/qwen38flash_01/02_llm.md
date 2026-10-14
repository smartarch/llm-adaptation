

## Strategy Description

My adaptation strategy follows these principles:

1. **Mandatory full protection of most threatened field**: Always assign exactly `drones_for_full_protection` drones to the highest-threat field. Select the closest drones to this field, preferring those already assigned to it (to minimize switching).

2. **Greedy full protection of remaining fields**: After protecting the most threatened field, use remaining drones to fully protect other threatened fields in order of threat level. Only commit drones if full protection can be achieved (avoids wasteful partial protection).

3. **Minimize switching**: Drones already in "protecting" state targeting a valid field are strongly preferred to stay there. Reassignment only happens when the most-threatened field needs closer drones.

4. **Avoid overprotection**: Never assign more than `drones_for_full_protection` to any field. Excess drones are redistributed.

5. **Minimize idle drones**: If fewer than half the drones are protecting, distribute remaining drones to partially protect other threatened fields (still better than idling).

6. **Full protection preference**: If a field can't be fully protected with available drones, skip it and try the next field.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Get all threatened fields sorted by threat level descending
        threatened_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # If no threats, all drones idle
        if not threatened_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        num_drones = len(components)
        assignments = {}
        available = list(components)

        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            return math.sqrt((drone.location.x - cx) ** 2 + (drone.location.y - cy) ** 2)

        def select_drones_for_field(field, count, available_drones):
            """Select up to `count` closest drones for `field`.
            Prefer drones already protecting this field (minimize switching)."""
            if count <= 0 or not available_drones:
                return []

            # Drones already protecting this target field (stay put)
            already_on_field = [
                d for d in available_drones
                if d.state == "protecting" and d.target_id == field.id
            ]
            already_on_field.sort(key=lambda d: distance_to_field(d, field))

            # All other available drones sorted by distance
            rest = [d for d in available_drones if d not in already_on_field]
            # Prefer idle drones over those moving/protecting elsewhere
            idle_rest = [d for d in rest if d.state == "idle"]
            other_rest = [d for d in rest if d.state != "idle"]
            idle_rest.sort(key=lambda d: distance_to_field(d, field))
            other_rest.sort(key=lambda d: distance_to_field(d, field))

            priority_order = already_on_field + idle_rest + other_rest
            selected = priority_order[:min(count, len(priority_order))]
            return selected

        # === Step 1: Mandatory full protection of most threatened field ===
        most_threatened = threatened_fields[0]
        needed = most_threatened.drones_for_full_protection
        count_to_assign = min(needed, len(available))

        selected = select_drones_for_field(most_threatened, count_to_assign, available)
        group_name = f"protecting {most_threatened.id}"
        for d in selected:
            assignments[d] = group_name
            available.remove(d)

        # === Step 2: Fully protect remaining threatened fields ===
        protected_field_ids = {most_threatened.id}
        total_protecting = len(assignments)

        for field in threatened_fields[1:]:
            needed = field.drones_for_full_protection
            if len(available) < needed:
                break  # Cannot fully protect; skip (prefer full over partial)

            selected = select_drones_for_field(field, needed, available)
            if len(selected) < needed:
                break

            group_name = f"protecting {field.id}"
            for d in selected:
                assignments[d] = group_name
                available.remove(d)

            protected_field_ids.add(field.id)
            total_protecting += len(selected)

        # === Step 3: Ensure at least half drones are protecting ===
        half_threshold = num_drones / 2.0
        if total_protecting < half_threshold and available:
            # Distribute spare drones to partially protect other threatened fields
            # Avoid fields that are already fully protected (no overprotection)
            for field in threatened_fields:
                if not available:
                    break
                if field.id in protected_field_ids:
                    continue  # Already fully protected, don't overprotect
                # Assign drones one at a time to different fields (spread thin but active)
                d = available[0]
                group_name = f"protecting {field.id}"
                assignments[d] = group_name
                available.remove(d)
                total_protecting += 1
                if total_protecting >= half_threshold:
                    break

        # === Step 4: Remaining drones go idle ===
        for d in available:
            assignments[d] = "idle"

        # === Apply all assignments ===
        for drone, group in assignments.items():
            environment.assign_group(drone, group)
```