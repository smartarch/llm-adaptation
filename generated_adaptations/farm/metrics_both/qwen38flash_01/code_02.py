from collections import defaultdict
import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        """
        Adaptation strategy for smart farm drone protection.
        
        group_id: identifier for the 'idle' group.
        Field protection groups are identified by str(field.id).
        """

        # --- Helper functions ---
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist(loc, center):
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.sqrt(dx * dx + dy * dy)

        # --- 1. Identify active fields sorted by threat (descending) ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # --- 2. Determine current drone states ---
        drone_loc = {}
        drone_current_field = {}  # drone_id -> field_id or None

        for d in components:
            drone_loc[d.id] = d.location
            if d.target_id is not None and d.state in ('protecting', 'moving_to_field'):
                drone_current_field[d.id] = d.target_id
            else:
                drone_current_field[d.id] = None

        # Group drones by current field assignment
        by_field = defaultdict(list)
        idle_drone_ids = []
        for d in components:
            fid = drone_current_field[d.id]
            if fid is None:
                idle_drone_ids.append(d.id)
            else:
                by_field[fid].append(d.id)

        # --- 3. Compute which drones to KEEP on their current field ---
        # For each active field, decide how many current drones to retain
        keep_assignments = {}  # field_id -> [drone_ids to keep]
        released_drones = list(idle_drone_ids)  # available for reassignment

        for f in active_fields:
            fid = f.id
            current_here = list(by_field.get(fid, []))
            needed = f.drones_for_full_protection

            if len(current_here) >= needed:
                # Keep only `needed` (closest ones); release excess
                center = field_center(f)
                current_here.sort(key=lambda did: dist(drone_loc[did], center))
                keep_assignments[fid] = current_here[:needed]
                released_drones.extend(current_here[needed:])
            else:
                # Keep all current drones here (we'll add more later)
                keep_assignments[fid] = list(current_here)

        # --- 4. Greedily fill fields to full protection using released drones ---
        final_field_drones = {}  # field_id -> [drone_ids assigned]
        available = list(released_drones)  # drones available for assignment

        for i, f in enumerate(active_fields):
            fid = f.id
            needed = f.drones_for_full_protection
            assigned = list(keep_assignments.get(fid, []))
            # Remove from available in case any were double-counted
            assigned_set = set(assigned)
            available = [did for did in available if did not in assigned_set]

            gap = needed - len(assigned)

            if gap > 0 and len(available) >= gap:
                # We can fully protect this field
                center = field_center(f)
                available.sort(key=lambda did: dist(drone_loc[did], center))
                take = available[:gap]
                assigned.extend(take)
                available = available[gap:]
                final_field_drones[fid] = assigned
            elif gap > 0 and len(available) > 0:
                # Cannot fully protect this field with remaining drones
                # For the top-priority field, we MUST fully protect → pull from lower fields
                if i == 0:
                    # Need to steal from lower-priority fields
                    still_need = gap - len(available)
                    assigned.extend(available)
                    available = []

                    for j in range(len(active_fields) - 1, i, -1):  # lowest priority first
                        if still_need <= 0:
                            break
                        other_f = active_fields[j]
                        other_fid = other_f.id
                        other_assigned = final_field_drones.get(other_fid,
                                           keep_assignments.get(other_fid, []))
                        other_need = other_f.drones_for_full_protection
                        # Spare = excess above need, or (if lower threat) allow partial reduction
                        spare = max(0, len(other_assigned) - other_need)
                        if spare == 0 and f.threat_level > other_f.threat_level * 1.5:
                            # Much higher threat: allow reducing other to partial (keep >=1)
                            spare = max(0, len(other_assigned) - 1)

                        steal_count = min(still_need, spare)
                        center = field_center(f)
                        other_assigned.sort(key=lambda did: dist(drone_loc[did], center))
                        stolen = other_assigned[:steal_count]
                        for did in stolen:
                            other_assigned.remove(did)
                            assigned.append(did)
                        final_field_drones[other_fid] = other_assigned
                        still_need -= steal_count

                    final_field_drones[fid] = assigned
                else:
                    # Not top priority: assign what we have for partial protection
                    # (better than idle, but this is suboptimal per requirements)
                    center = field_center(f)
                    available.sort(key=lambda did: dist(drone_loc[did], center))
                    take = list(available)
                    assigned.extend(take)
                    available = []
                    final_field_drones[fid] = assigned
            else:
                # Fully protected already or no gap
                final_field_drones[fid] = assigned

        # --- 5. Handle inactive fields (threat == 0): release their drones ---
        for f in environment.fields:
            fid = f.id
            if f.threat_level <= 0:
                # Drones here become idle
                for did in by_field.get(fid, []):
                    if did not in set().union(*[set(v) for v in final_field_drones.values()]):
                        available.append(did)

        # --- 6. If many drones still idle and fields remain, consider partial assignment ---
        # Only if we can assign them to a field that isn't yet fully protected
        total_drones = len(components)
        assigned_count = sum(len(v) for v in final_field_drones.values())

        if len(available) > total_drones * 0.4 and active_fields:
            # Assign surplus idle drones to the highest-threat under-protected field
            for f in active_fields:
                fid = f.id
                current_assigned = len(final_field_drones.get(fid, []))
                if current_assigned < f.drones_for_full_protection:
                    center = field_center(f)
                    available.sort(key=lambda did: dist(drone_loc[did], center))
                    to_assign = available[:f.drones_for_full_protection - current_assigned]
                    final_field_drones.setdefault(fid, []).extend(to_assign)
                    available = available[len(to_assign):]
                    break  # only top unfulfilled field

        # --- 7. Build final drone -> group mapping ---
        all_assigned_drones = set()
        for fid, dids in final_field_drones.items():
            for did in dids:
                all_assigned_drones.add(did)

        for d in components:
            did = d.id
            target_fid = None
            for fid, dids in final_field_drones.items():
                if did in dids:
                    target_fid = fid
                    break

            if target_fid is not None:
                # Assign to the field's protection group
                self._assign_group(d, str(target_fid))
            else:
                # Idle
                self._assign_group(d, group_id)

    def _assign_group(self, drone, group_name):
        """Assign a drone to a group by name."""
        try:
            drone.group = group_name
        except AttributeError:
            # Fallback: some frameworks use different attribute names
            try:
                drone.group_id = group_name
            except AttributeError:
                pass