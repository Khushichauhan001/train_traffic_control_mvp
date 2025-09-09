from typing import List, Dict, Tuple
from dataclasses import dataclass
from ..core.models import Train, Section, Block, TrainState, ScheduleDecision
from ..core.optimizer import HeuristicOptimizer
import random

@dataclass
class SimulationKPIs:
    total_trains: int = 0
    completed_trains: int = 0
    total_delay_min: float = 0.0
    section_utilization: float = 0.0
    throughput: float = 0.0  # trains per hour
    
    @property
    def avg_delay_min(self) -> float:
        return self.total_delay_min / self.completed_trains if self.completed_trains > 0 else 0.0

class Simulator:
    """
    Time-stepped simulation of train movements based on optimized schedule.
    """
    
    def __init__(self, section: Section, time_step: float = 1.0):
        self.section = section
        self.time_step = time_step
        self.optimizer = HeuristicOptimizer(section)
        self.block_map = {b.id: b for b in section.blocks}
    
    def simulate(self, trains: List[Train], max_time: float = 1440.0, 
                 disruptions: List[Dict] = None) -> Tuple[List[TrainState], SimulationKPIs]:
        """
        Run simulation with given trains and optional disruptions.
        Returns final train states and KPIs.
        """
        # Initialize train states
        train_states = {t.id: TrainState(train=t, time_min=t.dep_time_min) for t in trains}
        
        # Get initial schedule
        schedule = self.optimizer.optimize(trains)
        
        # Track block occupancy over time
        block_occupancy = {b.id: None for b in self.section.blocks}
        
        # Simulation variables
        current_time = 0.0
        kpis = SimulationKPIs(total_trains=len(trains))
        block_busy_time = {b.id: 0.0 for b in self.section.blocks}
        
        # Simulation loop
        while current_time <= max_time:
            # Apply disruptions if any
            if disruptions:
                for disruption in disruptions:
                    if disruption['time'] == int(current_time):
                        self._apply_disruption(disruption, train_states)
                        # Re-optimize after disruption
                        active_trains = [ts.train for ts in train_states.values() if not ts.finished]
                        if active_trains:
                            schedule = self.optimizer.optimize(active_trains, current_time)
            
            # Update train positions
            for train_id, state in train_states.items():
                if state.finished:
                    continue
                
                train = state.train
                
                # Check if train should start
                if state.route_index == 0 and current_time >= train.dep_time_min:
                    first_block = train.route[0]
                    scheduled_entry = schedule.get_entry(train_id, first_block)
                    
                    if scheduled_entry and current_time >= scheduled_entry:
                        # Check if block is free
                        if block_occupancy[first_block] is None:
                            block_occupancy[first_block] = train_id
                            state.location = first_block
                            state.time_min = current_time
                
                # Move train through blocks
                elif state.location:
                    current_block_id = state.location
                    block = self.block_map[current_block_id]
                    
                    # Calculate time in block
                    travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                    dwell_time = train.dwell_min if block.station else 0
                    total_time = travel_time + dwell_time
                    
                    # Check if train should exit current block
                    if current_time >= state.time_min + total_time:
                        # Clear current block
                        block_occupancy[current_block_id] = None
                        
                        # Move to next block
                        state.route_index += 1
                        if state.route_index < len(train.route):
                            next_block = train.route[state.route_index]
                            scheduled_entry = schedule.get_entry(train_id, next_block)
                            
                            if scheduled_entry and current_time >= scheduled_entry:
                                # Check if next block is free
                                if block_occupancy[next_block] is None:
                                    block_occupancy[next_block] = train_id
                                    state.location = next_block
                                    state.time_min = current_time
                        else:
                            # Train has completed its route
                            state.finished = True
                            state.location = None
                            completion_time = current_time
                            scheduled_completion = sum([
                                (self.block_map[bid].length_km / min(train.max_speed_kmph, self.block_map[bid].max_speed_kmph)) * 60 +
                                (train.dwell_min if self.block_map[bid].station else 0)
                                for bid in train.route
                            ]) + train.dep_time_min
                            state.delay_min = max(0, completion_time - scheduled_completion)
                            kpis.completed_trains += 1
                            kpis.total_delay_min += state.delay_min
            
            # Track block utilization
            for block_id, occupant in block_occupancy.items():
                if occupant is not None:
                    block_busy_time[block_id] += self.time_step
            
            current_time += self.time_step
        
        # Calculate final KPIs
        total_block_time = len(self.section.blocks) * max_time
        total_busy_time = sum(block_busy_time.values())
        kpis.section_utilization = (total_busy_time / total_block_time) * 100 if total_block_time > 0 else 0
        kpis.throughput = (kpis.completed_trains / (max_time / 60)) if max_time > 0 else 0
        
        return list(train_states.values()), kpis
    
    def _apply_disruption(self, disruption: Dict, train_states: Dict[str, TrainState]):
        """
        Apply a disruption to the simulation (e.g., train delay, block failure).
        """
        if disruption['type'] == 'train_delay':
            train_id = disruption['train_id']
            delay = disruption['delay_min']
            if train_id in train_states:
                train_states[train_id].train.dep_time_min += delay
        elif disruption['type'] == 'block_failure':
            # In a real system, this would affect block availability
            pass
