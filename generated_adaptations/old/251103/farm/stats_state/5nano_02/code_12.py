from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Strategy overview (implemented here in code comments for clarity):
    - Objective: aggressively protect the most-threatened field by fully staffing it to its required level
      using the closest drones, while minimizing unnecessary movement between fields.
    - Primary rule: always fill the top-threat field to its drones_for_full_protection using the nearest
      available drones (preferring drones that are idle or already en route, then recycled from other fields).
      Keep drones already protecting the top field in its group when possible.
    - Secondary rule: after top field is adequately protected, bolster other threatened fields in
      descending order of threat level, using the closest remaining drones.
    - Movement considerations: prioritize drones near a target field to reduce travel time; avoid thrashing
      by reusing drones already near the top field before scattering them to others.
    - Assignment policy: every drone must be assigned to exactly one group. If a target group is not valid,
      the drone defaults to "idle".
    - This implementation uses a simple but effective proximity-based allocation that explicitly handles
      drones in any state (idle, moving_to_field, protecting) to minimize wasted transit time.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist2_to_point(drone, cx, cy):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", None)
            y = getattr(loc, "y", None)
            if x is None or y is None:
                try:
                    x, y = float(loc[0]), float(loc[1])
                except Exception:
                    return float("inf")
            return (float(x) - cx) ** 2 + (float(y) - cy) ** 2

        def safe_assign(drone, group_name):
            if group_name in group_ids:
                environment.assign_group(drone, group_name)
            else:
                environment.assign_group(drone, "idle")

        # Step 0: If no threat fields, idle everyone
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            for d in components:
                safe_assign(d, "idle")
            return

        # Step 1: Identify the top threatened field
        top_field = max(fields_with_threat, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"

        assigned = set()

        # Step 2: Preserve drones already protecting the top field
        for d in components:
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id:
                safe_assign(d, top_group)
                assigned.add(id(d))

        # Step 3: Fill the top field to its full protection using closest available drones
        required = int(getattr(top_field, "drones_for_full_protection", 0))
        current = int(getattr(top_field, "protecting_drones", 0))
        missing = max(0, required - current)

        if missing > 0:
            cx, cy = field_center(top_field)
            candidates = []
            for d in components:
                if id(d) in assigned:
                    continue
                dist = dist2_to_point(d, cx, cy)
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            for _, drone in candidates:
                if missing <= 0:
                    break
                safe_assign(drone, top_group)
                assigned.add(id(drone))
                missing -= 1

        # Step 4: Bolster other threatened fields (secondary protection) in descending threat
        other_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0 and f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for field in other_fields:
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = int(getattr(field, "protecting_drones", 0))
            missing = max(0, required - current)
            if missing <= 0:
                continue

            cx, cy = field_center(field)
            candidates = []
            for d in components:
                if id(d) in assigned:
                    continue
                dist = dist2_to_point(d, cx, cy)
                candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])

            group_name = f"protecting {field.id}"
            for _, drone in candidates:
                if missing <= 0:
                    break
                safe_assign(drone, group_name)
                assigned.add(id(drone))
                missing -= 1

        # Step 5: Any remaining drones go idle
        for d in components:
            if id(d) not in assigned:
                safe_assign(d, "idle")