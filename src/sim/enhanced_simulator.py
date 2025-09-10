from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from ..core.models import Train, Section, Block, TrainState, ScheduleDecision
from ..core.optimizer import HeuristicOptimizer
from ..core.safety_validator import CollisionDetector, SafetyViolation
import random

@dataclass
class Event:
    """Represents a system event"""
    timestamp: float
    event_type: str  # ARRIVAL, DEPARTURE, CROSSING, DELAY, WARNING, ERROR
    train_id: Optional[str]
    block_id: Optional[str]
    message: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'time_str': f"{int(self.timestamp//60):02d}:{int(self.timestamp%60):02d}",
            'event_type': self.event_type,
            'train_id': self.train_id,
            'block_id': self.block_id,
            'message': self.message,
            'severity': self.severity
        }

@dataclass
class EnhancedKPIs:
    """Extended KPIs with more metrics"""
    total_trains: int = 0
    completed_trains: int = 0
    active_trains: int = 0
    total_delay_min: float = 0.0
    max_delay_min: float = 0.0
    section_utilization: float = 0.0
    throughput: float = 0.0
    on_time_performance: float = 0.0  # % trains with delay < 5 min
    safety_score: float = 100.0  # 100 = perfect, reduces with violations
    total_distance_km: float = 0.0
    avg_speed_kmph: float = 0.0
    
    @property
    def avg_delay_min(self) -> float:
        return self.total_delay_min / self.completed_trains if self.completed_trains > 0 else 0.0

class EnhancedSimulator:
    """
    Advanced simulator with event logging and real-time monitoring
    """
    
    def __init__(self, section: Section, time_step: float = 0.5):
        self.section = section
        self.time_step = time_step
        self.optimizer = HeuristicOptimizer(section)
        self.collision_detector = CollisionDetector(section)
        self.block_map = {b.id: b for b in section.blocks}
        self.events: List[Event] = []
        self.current_time = 0.0
        
    def simulate(self, trains: List[Train], max_time: float = 1440.0, 
                 disruptions: List[Dict] = None, realtime_callback=None) -> Tuple[List[TrainState], EnhancedKPIs, List[Event]]:
        """
        Run enhanced simulation with event logging and safety checks
        """
        # Initialize
        self.events = []
        train_states = {t.id: TrainState(train=t, time_min=t.dep_time_min) for t in trains}
        
        # Get initial schedule and validate
        schedule = self.optimizer.optimize(trains)
        is_safe, violations = self.collision_detector.validate_schedule(schedule, trains)
        
        # Log safety check results
        if not is_safe:
            for violation in violations:
                if violation.severity == "critical":
                    self._log_event(0, "ERROR", None, violation.block_id, 
                                  violation.message, "CRITICAL")
        else:
            self._log_event(0, "SYSTEM", None, None, 
                          "Schedule validated - No collision risks detected", "INFO")
        
        # Initialize tracking variables
        block_occupancy = {b.id: None for b in self.section.blocks}
        kpis = EnhancedKPIs(total_trains=len(trains))
        block_busy_time = {b.id: 0.0 for b in self.section.blocks}
        train_distances = {t.id: 0.0 for t in trains}
        train_times = {t.id: 0.0 for t in trains}
        
        # Log simulation start
        self._log_event(0, "SYSTEM", None, None, 
                      f"Enhanced simulation started with {len(trains)} trains", "INFO")
        
        # Main simulation loop
        self.current_time = 0.0
        while self.current_time <= max_time:
            # Handle disruptions
            if disruptions:
                for disruption in disruptions:
                    if abs(disruption['time'] - self.current_time) < self.time_step:
                        self._apply_disruption(disruption, train_states)
                        self._log_event(self.current_time, "DISRUPTION", 
                                      disruption.get('train_id'), None,
                                      f"Disruption: {disruption['type']}", "WARNING")
                        
                        # Re-optimize if needed
                        active_trains = [ts.train for ts in train_states.values() if not ts.finished]
                        if active_trains:
                            schedule = self.optimizer.optimize(active_trains, self.current_time)
                            is_safe, new_violations = self.collision_detector.validate_schedule(schedule, active_trains)
                            if not is_safe:
                                for v in new_violations:
                                    if v.severity == "critical":
                                        self._log_event(self.current_time, "WARNING", None, v.block_id,
                                                      f"Post-disruption: {v.message}", "WARNING")
            
            # Update active train count
            kpis.active_trains = sum(1 for ts in train_states.values() 
                                    if not ts.finished and ts.location is not None)
            
            # Process each train
            for train_id, state in train_states.items():
                if state.finished:
                    continue
                
                train = state.train
                
                # Train waiting to depart
                if state.route_index == 0 and self.current_time >= train.dep_time_min:
                    first_block = train.route[0]
                    scheduled_entry = schedule.get_entry(train_id, first_block)
                    
                    if scheduled_entry and self.current_time >= scheduled_entry:
                        # Verify block is actually free
                        if self.collision_detector.verify_block_clearance(first_block, self.current_time, schedule, trains):
                            if block_occupancy[first_block] is None:
                                block_occupancy[first_block] = train_id
                                state.location = first_block
                                state.time_min = self.current_time
                                self._log_event(self.current_time, "DEPARTURE", train_id, first_block,
                                              f"Train {train_id} departed from {first_block}", "INFO")
                        else:
                            self._log_event(self.current_time, "WARNING", train_id, first_block,
                                          f"Block {first_block} not clear for {train_id} - Safety hold", "WARNING")
                
                # Train in transit
                elif state.location:
                    current_block_id = state.location
                    block = self.block_map[current_block_id]
                    
                    # Update distance tracking
                    if train_id in train_distances:
                        train_distances[train_id] += (block.length_km * self.time_step / 60) / \
                                                    ((block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60)
                        train_times[train_id] += self.time_step
                    
                    # Calculate time in block
                    travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                    dwell_time = train.dwell_min if block.station else 0
                    total_time = travel_time + dwell_time
                    
                    # Check if train should exit current block
                    if self.current_time >= state.time_min + total_time:
                        # Clear current block
                        block_occupancy[current_block_id] = None
                        
                        # Log station arrival if applicable
                        if block.station:
                            self._log_event(self.current_time, "ARRIVAL", train_id, current_block_id,
                                          f"Train {train_id} arrived at station {block.station}", "INFO")
                        
                        # Move to next block
                        state.route_index += 1
                        if state.route_index < len(train.route):
                            next_block = train.route[state.route_index]
                            scheduled_entry = schedule.get_entry(train_id, next_block)
                            
                            if scheduled_entry and self.current_time >= scheduled_entry:
                                # Double-check safety
                                if self.collision_detector.verify_block_clearance(next_block, self.current_time, schedule, trains):
                                    if block_occupancy[next_block] is None:
                                        block_occupancy[next_block] = train_id
                                        state.location = next_block
                                        state.time_min = self.current_time
                                        
                                        # Check for crossing
                                        if self._is_crossing_point(next_block, train_states):
                                            self._log_event(self.current_time, "CROSSING", train_id, next_block,
                                                          f"Train {train_id} crossing at {next_block}", "INFO")
                                else:
                                    self._log_event(self.current_time, "WARNING", train_id, next_block,
                                                  f"Safety hold: Block {next_block} not clear", "WARNING")
                        else:
                            # Train completed
                            state.finished = True
                            state.location = None
                            completion_time = self.current_time
                            
                            # Calculate final delay
                            scheduled_completion = sum([
                                (self.block_map[bid].length_km / min(train.max_speed_kmph, self.block_map[bid].max_speed_kmph)) * 60 +
                                (train.dwell_min if self.block_map[bid].station else 0)
                                for bid in train.route
                            ]) + train.dep_time_min
                            
                            state.delay_min = max(0, completion_time - scheduled_completion)
                            kpis.completed_trains += 1
                            kpis.total_delay_min += state.delay_min
                            kpis.max_delay_min = max(kpis.max_delay_min, state.delay_min)
                            
                            self._log_event(self.current_time, "COMPLETION", train_id, None,
                                          f"Train {train_id} completed journey. Delay: {state.delay_min:.1f} min", 
                                          "INFO" if state.delay_min < 5 else "WARNING")
            
            # Track block utilization
            for block_id, occupant in block_occupancy.items():
                if occupant is not None:
                    block_busy_time[block_id] += self.time_step
            
            # Callback for real-time updates (every 10 time steps for better visibility)
            if realtime_callback and int(self.current_time * 2) % 20 == 0:  # Every 10 seconds
                should_continue = realtime_callback(self.current_time, train_states, kpis, self.events[-10:])
                if should_continue == False:  # Explicit check for stop signal
                    self._log_event(self.current_time, "SYSTEM", None, None,
                                  "Simulation stopped by user request", "INFO")
                    break
            
            self.current_time += self.time_step
        
        # Calculate final KPIs
        total_block_time = len(self.section.blocks) * max_time
        total_busy_time = sum(block_busy_time.values())
        kpis.section_utilization = (total_busy_time / total_block_time) * 100 if total_block_time > 0 else 0
        kpis.throughput = (kpis.completed_trains / (max_time / 60)) if max_time > 0 else 0
        
        # Calculate on-time performance
        on_time_count = sum(1 for ts in train_states.values() if ts.finished and ts.delay_min < 5)
        kpis.on_time_performance = (on_time_count / kpis.completed_trains * 100) if kpis.completed_trains > 0 else 0
        
        # Calculate average speed
        total_distance = sum(train_distances.values())
        total_time_hours = sum(train_times.values()) / 60
        kpis.total_distance_km = total_distance
        kpis.avg_speed_kmph = (total_distance / total_time_hours) if total_time_hours > 0 else 0
        
        # Calculate safety score (decreases with violations)
        critical_events = sum(1 for e in self.events if e.severity == "CRITICAL")
        warning_events = sum(1 for e in self.events if e.severity == "WARNING")
        kpis.safety_score = max(0, 100 - (critical_events * 20) - (warning_events * 5))
        
        # Log simulation completion
        self._log_event(self.current_time, "SYSTEM", None, None,
                      f"Simulation completed after {self.current_time:.1f} minutes", "INFO")
        
        return list(train_states.values()), kpis, self.events
    
    def _log_event(self, timestamp: float, event_type: str, train_id: Optional[str], 
                   block_id: Optional[str], message: str, severity: str):
        """Log an event"""
        event = Event(
            timestamp=timestamp,
            event_type=event_type,
            train_id=train_id,
            block_id=block_id,
            message=message,
            severity=severity
        )
        self.events.append(event)
    
    def _is_crossing_point(self, block_id: str, train_states: Dict[str, TrainState]) -> bool:
        """Check if this is a crossing point for trains"""
        trains_approaching = 0
        for state in train_states.values():
            if not state.finished and block_id in state.train.route:
                trains_approaching += 1
        return trains_approaching > 1
    
    def _apply_disruption(self, disruption: Dict, train_states: Dict[str, TrainState]):
        """Apply a disruption to the simulation"""
        if disruption['type'] == 'train_delay':
            train_id = disruption['train_id']
            delay = disruption['delay_min']
            if train_id in train_states:
                train_states[train_id].train.dep_time_min += delay
        elif disruption['type'] == 'block_failure':
            # In production, this would affect block availability
            pass
