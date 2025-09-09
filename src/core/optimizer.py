from typing import List, Dict, Tuple
from .models import Train, Section, Block, ScheduleDecision
import heapq

class HeuristicOptimizer:
    """
    Simplified optimizer using priority-based scheduling with headway constraints.
    """
    
    def __init__(self, section: Section):
        self.section = section
        self.block_map = {b.id: b for b in section.blocks}
    
    def optimize(self, trains: List[Train], current_time: float = 0.0) -> ScheduleDecision:
        """
        Schedule trains by priority, respecting headway and block occupancy.
        Returns a ScheduleDecision with entry times for each train at each block.
        """
        schedule = ScheduleDecision()
        block_occupancy = {}  # block_id -> list of (entry_time, exit_time, train_id)
        
        # Sort trains by priority (lower is higher priority) and then by departure time
        sorted_trains = sorted(trains, key=lambda t: (t.priority, t.dep_time_min))
        
        for train in sorted_trains:
            train_schedule = self._schedule_train(train, block_occupancy, current_time)
            for block_id, entry_time in train_schedule.items():
                schedule.set_entry(train.id, block_id, entry_time)
        
        return schedule
    
    def _schedule_train(self, train: Train, block_occupancy: Dict, current_time: float) -> Dict[str, float]:
        """
        Schedule a single train through its route, respecting constraints.
        """
        train_schedule = {}
        entry_time = max(train.dep_time_min, current_time)
        
        for block_id in train.route:
            block = self.block_map[block_id]
            
            # Check for conflicts and adjust entry time if needed
            if block_id in block_occupancy:
                for occ_entry, occ_exit, occ_train_id in block_occupancy[block_id]:
                    if entry_time < occ_exit + self.section.headway_min:
                        # Delay this train to maintain headway
                        entry_time = occ_exit + self.section.headway_min
            
            train_schedule[block_id] = entry_time
            
            # Calculate exit time
            travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
            dwell_time = train.dwell_min if block.station else 0
            exit_time = entry_time + travel_time + dwell_time
            
            # Update block occupancy
            if block_id not in block_occupancy:
                block_occupancy[block_id] = []
            block_occupancy[block_id].append((entry_time, exit_time, train.id))
            
            # Next block entry time is this block's exit time
            entry_time = exit_time
        
        return train_schedule
    
    def handle_crossing(self, train1: Train, train2: Train, meeting_block: str) -> Tuple[str, str]:
        """
        Determine which train should wait at a loop/station for crossing.
        Returns (waiting_train_id, proceeding_train_id)
        """
        # Simple heuristic: higher priority train proceeds, lower priority waits
        if train1.priority <= train2.priority:
            return (train2.id, train1.id)
        else:
            return (train1.id, train2.id)
