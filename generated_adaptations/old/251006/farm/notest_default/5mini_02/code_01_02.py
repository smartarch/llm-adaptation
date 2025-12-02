# SmartFarmAdaptation
#
# Reasoning and strategy:
# - The farm has multiple fields, each with a threat_level and a required number of drones
#   for full protection (drones_for_full_protection).
# - The adaptation policy must always fully protect the single highest-threat field,
#   using the closest drones available until the required number is reached.
# - If the highest-threat field is already fully protected (i.e., there are already
#   >= drones_for_full_protection drones protecting it), those drones stay assigned there.
# - To choose drones to send, we:
#     * Count drones already protecting the chosen field (state == "protecting" and
#       target_id == field.id).
#     * If more drones are needed, pick the nearest drones among the remaining drones
#       (this may include idle drones, moving drones, or drones protecting other fields).
# - Any drone not required to achieve full protection of the chosen highest-threat field
#   is assigned to "idle". (One could also assign them to protect other fields, but the
#   requirement prioritized a single field.)
# - All assignments are explicit: every component is assigned to exactly one group on each call.
#
# Implementation details:
# - We locate the highest-threat field among fields with threat_level > 0. If there are
#   no threatened fields, we assign all drones to "idle".
# - For distance computations, we use the field center: ((left+right)/2, (top+bottom)/2).
# - We respect the provided group_ids: if the expected protecting group name for the selected
#   field is not present in group_ids, we fall back to assigning drones to "idle".
#
# Note: The rest of the runtime (movement, updating of component states) is managed
# outside this adaptation function. This strategy only issues group assignment commands.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: distance squared between drone and field center
        def dist2(drone_loc, center):
            dx = drone_loc.x - center[0]
            dy = drone_loc.y - center[1]
            return dx * dx + dy * dy

        # Build list of threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Default: assign all to idle if no threatened fields
        idle_group = "idle"
        if idle_group not in group_ids:
            # If for some reason "idle" is not a valid group, try a safe fallback to first group_id
            idle_group = group_ids[0] if group_ids else "idle"

        if not threatened_fields:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Select the highest-threat field (tie-breaking by id for determinism)
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, str(getattr(f, "id", ""))))

        protect_group_name = f"protecting {target_field.id}"
        use_protect_group = protect_group_name if protect_group_name in group_ids else None

        # Determine how many drones are needed for full protection
        needed = int(getattr(target_field, "drones_for_full_protection", 0))

        # Compute center of the field
        center_x = (target_field.left + target_field.right) / 2.0
        center_y = (target_field.top + target_field.bottom) / 2.0
        center = (center_x, center_y)

        # Identify drones already protecting this field (we treat state=="protecting" and target_id==field.id as protecting)
        already_protecting = []
        others = []
        for comp in components:
            try:
                if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == target_field.id:
                    already_protecting.append(comp)
                else:
                    others.append(comp)
            except Exception:
                # In case of unexpected component structure, treat as other
                others.append(comp)

        num_already = len(already_protecting)

        # If already enough drones are protecting, keep them and idle the rest
        if num_already >= needed:
            # Assign the protecting drones to the protecting group (if group exists)
            for comp in already_protecting:
                if use_protect_group:
                    environment.assign_group(comp, use_protect_group)
                else:
                    environment.assign_group(comp, idle_group)
            # Idle everyone else
            for comp in others:
                environment.assign_group(comp, idle_group)
            return

        # Need additional drones: choose closest ones from 'others'
        needed_more = needed - num_already

        # Sort 'others' by distance to field center
        others_sorted = sorted(others, key=lambda c: dist2(getattr(c, "location"), center))

        # Select the top needed_more drones (if not enough, select all)
        chosen_for_transfer = set(others_sorted[:needed_more])

        # Assign groups:
        # - already_protecting -> protecting group (if available) else idle
        # - chosen_for_transfer -> protecting group (if available) else idle
        # - remaining drones -> idle
        for comp in components:
            if comp in already_protecting:
                if use_protect_group:
                    environment.assign_group(comp, use_protect_group)
                else:
                    environment.assign_group(comp, idle_group)
            elif comp in chosen_for_transfer:
                if use_protect_group:
                    environment.assign_group(comp, use_protect_group)
                else:
                    environment.assign_group(comp, idle_group)
            else:
                environment.assign_group(comp, idle_group)