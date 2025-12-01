from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist_to_field_center(self, component, field):
        # compute Euclidean distance from drone to field center
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = component.location.x - cx
        dy = component.location.y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Find fields that need protection
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, put everyone idle
        if not threatened_fields:
            idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Choose the single field with the highest threat_level
        target_field = max(threatened_fields, key=lambda f: f.threat_level)
        target_group = f"protecting {target_field.id}"
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # If the protecting group name isn't valid for some reason, fallback everyone to idle
        if target_group not in group_ids:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Number of drones required for full protection
        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Prepare categorized lists of (component, distance)
        protecting_here = []
        moving_here = []
        idle_list = []
        moving_others = []
        protecting_others = []

        for c in components:
            d = self._dist_to_field_center(c, target_field)
            state = getattr(c, "state", None)
            target_id = getattr(c, "target_id", None)
            if state == "protecting" and target_id == target_field.id:
                protecting_here.append((c, d))
            elif state == "moving_to_field" and target_id == target_field.id:
                moving_here.append((c, d))
            elif state == "idle":
                idle_list.append((c, d))
            elif state == "moving_to_field":
                moving_others.append((c, d))
            elif state == "protecting":
                protecting_others.append((c, d))
            else:
                # any other/unrecognized state treat as idle-like
                idle_list.append((c, d))

        # Sort each category by distance ascending
        protecting_here.sort(key=lambda x: x[1])
        moving_here.sort(key=lambda x: x[1])
        idle_list.sort(key=lambda x: x[1])
        moving_others.sort(key=lambda x: x[1])
        protecting_others.sort(key=lambda x: x[1])

        # Select drones to assign to protect the target field according to priority until required reached
        selected_ids = set()
        selected_order = []

        def take_from_list(cat):
            for comp, _ in cat:
                cid = id(comp)
                if cid in selected_ids:
                    continue
                selected_ids.add(cid)
                selected_order.append(comp)
                if len(selected_order) >= required:
                    return True
            return len(selected_order) >= required

        # Priority 1: already protecting here
        take_from_list(protecting_here)
        # Priority 2: moving here
        if len(selected_order) < required:
            take_from_list(moving_here)
        # Priority 3: idle drones
        if len(selected_order) < required:
            take_from_list(idle_list)
        # Priority 4: moving to other fields
        if len(selected_order) < required:
            take_from_list(moving_others)
        # Priority 5: protecting other fields
        if len(selected_order) < required:
            take_from_list(protecting_others)

        # Assign groups: selected drones -> target_group, all others -> idle_group
        for c in components:
            if id(c) in selected_ids:
                environment.assign_group(c, target_group)
            else:
                environment.assign_group(c, idle_group)