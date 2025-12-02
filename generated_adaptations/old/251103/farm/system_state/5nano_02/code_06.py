"""
Adaptive strategy rationale (embedded in code as a module docstring):

Goal improvement:
- More robustly protect the field with the highest threat by accounting not only for drones currently
  protecting it, but also those en route to protect it (state "moving_to_field" targeting the top field).
- Allocate drones to achieve full protection using the nearest available drones first, while preserving drones
  already committed to the top field.
- If no field has threat > 0, keep all drones idle.

Key decisions:
- Identify top_field as the field with maximum threat_level (> 0).
- Consider allocated_to_top as drones whose target_id == top_field.id and whose state is either "protecting" or "moving_to_field".
- If allocated_to_top >= drones_for_full_protection, mark all these drones as protecting the top field and idle the rest.
- Otherwise, select the closest non-allocated drones to fill the shortfall, and assign all selected drones to the group "protecting {top_field.id}".
- Drones outside the selected set go to "idle".

This approach respects the requirement to fully protect the highest-threat field first while making use of in-flight drones
and minimizing unnecessary reassignments.
"""

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify fields with threat > 0
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If there are no threatened fields, all drones idle
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Choose the top threat field
        top_field = max(fields_with_threat, key=lambda fld: fld.threat_level)
        top_group = f"protecting {top_field.id}"

        # 3) Compute center of the field for proximity calculations
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        # 4) Drones already allocated to top field: protecting or moving toward it
        allocated = set()
        for d in components:
            if getattr(d, "target_id", None) == top_field.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                allocated.add(d)

        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # 5) If already fully allocated, keep them there; others idle
        if len(allocated) >= max(needed, 0):
            for d in components:
                if d in allocated:
                    environment.assign_group(d, top_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # 6) Need more drones to reach full protection
        remaining = max(0, needed - len(allocated))

        # 7) Candidate drones: those not yet allocated
        candidates = [d for d in components if d not in allocated]

        # 8) Sort candidates by distance to field center (closest first)
        def dist2(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            return (loc.x - center_x) ** 2 + (loc.y - center_y) ** 2

        candidates.sort(key=dist2)

        # 9) Select the closest drones to fill the gap
        selected = set(allocated)
        if remaining > 0:
            for c in candidates[:remaining]:
                selected.add(c)

        # 10) Assign groups: selected drones to top_group; others to idle
        for d in components:
            if d in selected:
                environment.assign_group(d, top_group)
            else:
                environment.assign_group(d, "idle")