import math
import pandas as pd
import numpy as np

class DG_instance:
    def __init__(self,SignallingEscrowMinLockTime,ProposalExecutionMinTimelock,FirstSealRageQuitSupport,SecondSealRageQuitSupport,VetoSignallingDeactivationMaxDuration,
               DynamicTimelockMinDuration,DynamicTimelockMaxDuration,VetoSignallingMinActiveDuration,RageQuitExtensionDelay,RageQuitEthClaimMinTimelock,RageQuitEthClaimTimelockGrowthStartSeqNumber,
               RageQuitEthClaimTimelockGrowthCoeffs,VetoCooldownDuration):
        self.signal_esc_min_lock_time = SignallingEscrowMinLockTime
        self.proposal_exec_min_time_lock = ProposalExecutionMinTimelock
        self.first_seal_rage_quit = FirstSealRageQuitSupport
        self.second_seal_rage_quit = SecondSealRageQuitSupport
        self.veto_signalling_deact_max_dur = VetoSignallingDeactivationMaxDuration
        self.dynamic_time_lock_min_dur = DynamicTimelockMinDuration
        self.dynamic_time_lock_max_dur = DynamicTimelockMaxDuration
        self.veto_signalling_min_active_dur = VetoSignallingMinActiveDuration
        self.rage_quit_extension_delay = RageQuitExtensionDelay
        self.rage_quit_eth_claim_min_time_lock = RageQuitEthClaimMinTimelock
        self.rage_quit_growth_start_seq_number = RageQuitEthClaimTimelockGrowthStartSeqNumber
        self.rage_quit_growth_coef = RageQuitEthClaimTimelockGrowthCoeffs
        self.veto_cooldown_duration = VetoCooldownDuration
        self.rage_quits=[]
        self.log=[]
        self.current_state = 'normal'
        self.veto_signalling_duration = 0
        self.stETH_in_opposition = 0
        self.total_stETH = 0
        self.others_eth_staked = 0
        self.last_veto_signalling_start = 0
        self.last_veto_reactivation_start = 0
        self.last_veto_deactivation_start = 0
        self.last_veto_cooldown_start = 0
        self.lido_exit_share = 0.3
        self.rage_quits_amount = 0

    def reset_dg_instance(self):
        self.current_state='normal'
        self.rage_quits=[]
        self.log=[]
        self.veto_signalling_duration = 0
        self.stETH_in_opposition = 0
        self.total_stETH = 0
        self.others_eth_staked = 0
        self.last_veto_signalling_start = 0
        self.last_veto_reactivation_start = 0
        self.last_veto_deactivation_start = 0
        self.last_veto_cooldown_start = 0
        self.lido_exit_share = 0.3
        self.rage_quits_amount = 0


    def calculate_veto_signalling_duration(self,total_steth,opposition_steth):
        if opposition_steth/total_steth < self.first_seal_rage_quit:
            return 0
        if opposition_steth/total_steth > self.first_seal_rage_quit and opposition_steth/total_steth <= self.second_seal_rage_quit:
            return int(self.dynamic_time_lock_min_dur+(opposition_steth/total_steth-self.first_seal_rage_quit)/(self.second_seal_rage_quit-self.first_seal_rage_quit)*\
                (self.dynamic_time_lock_max_dur-self.dynamic_time_lock_min_dur))
        if opposition_steth/total_steth >= self.second_seal_rage_quit:
            return self.dynamic_time_lock_max_dur
        
    def setup_simulation(self,simulation):
        self.total_stETH = simulation.initial_stETH
        self.others_eth_staked = simulation.initial_others_eth_staked
        self.stETH_in_opposition = simulation.initial_stETH_in_opposition


    def process_simulation(self,simulation):

        self.setup_simulation(simulation)

        for day in range(len(simulation.events_flow)):

            if not simulation.events_flow.iloc[day,2]:         
              continue

            events_flow=sorted(simulation.events_flow.iloc[day,2], key=lambda x:x['timestamp'])
            event_num=0
            event_amount=len(events_flow)
      

            while event_num<event_amount:  
                 assert self.stETH_in_opposition >=0, "Negative value of stETH in opposition, try rewrite events data"
                 assert self.total_stETH >=0, "Negative value of total stETH, try rewrite events data"
                 assert self.others_eth_staked >=0, "Negative value of others staked ETH, try rewrite events data"
                 assert self.stETH_in_opposition <= self.total_stETH, "More stETH in opposition, then currently exist, try rewrite event data"
            
                 if events_flow[event_num]['method'] == 'change_others_staked_eth_amount':
                     self.others_eth_staked += int(events_flow[event_num]['amount'])
                 elif events_flow[event_num]['method'] == 'change_stETH_amount':
                     self.total_stETH += int(events_flow[event_num]['amount'])
                 elif events_flow[event_num]['method'] == 'change_opposition_stETH_amount':
                     self.stETH_in_opposition += int(events_flow[event_num]['amount'])         
                

                #Normal flow
                 if self.stETH_in_opposition/self.total_stETH<self.first_seal_rage_quit and self.current_state=='normal':
                     event_num +=1
                     continue           
                 
                 #Signalling time change
                 if events_flow[event_num]['method'] != 'signalling_end' and (self.current_state == 'veto_signalling') :
                     new_waiting_time=int(self.calculate_veto_signalling_duration(self.total_stETH,self.stETH_in_opposition))
                     self.veto_signalling_duration=new_waiting_time-(events_flow[event_num]['timestamp']-self.last_veto_signalling_start)
                     simulation.add_event({'timestamp': events_flow[event_num]['timestamp']+self.veto_signalling_duration, 'method': 'signalling_end','amount':0})

                #Normal -> Signalling transition
                 if self.stETH_in_opposition / self.total_stETH >self.first_seal_rage_quit and (self.current_state == 'normal' or events_flow[event_num]['method'] == 'rage_quit_end'):
                     self.current_state='veto_signalling'
                     self.veto_signalling_duration=max(self.veto_signalling_min_active_dur,int(self.calculate_veto_signalling_duration(self.total_stETH,self.stETH_in_opposition)))
                     self.last_veto_signalling_start = events_flow[event_num]['timestamp']
                     simulation.add_event({'timestamp': events_flow[event_num]['timestamp']+self.veto_signalling_duration, 'method': 'signalling_end','amount':0})
                     self.log.append({'event':'enter_veto_signalling','timestamp':events_flow[event_num]['timestamp']})
                
                #Conversion to rage quit protocol
                 if self.stETH_in_opposition / self.total_stETH > self.second_seal_rage_quit and self.last_veto_signalling_start+self.veto_signalling_duration <= events_flow[event_num]['timestamp'] and self.current_state == 'veto_signalling':
                     self.rage_quits_amount +=1
                     self.rage_quits.append({'seq_number':self.rage_quits_amount,'eth_to_exit':self.stETH_in_opposition,'timestamp':events_flow[event_num]['timestamp'],'stETH_amount':self.total_stETH,'others_stacked_eth_amount':self.others_eth_staked})
                     self.current_state = 'rage_quit'
                     waiting_time=self.calculate_rage_quit_duration(self.rage_quits[-1],self.lido_exit_share)
                     self.total_stETH -= self.stETH_in_opposition
                     self.stETH_in_opposition = 0
                     self.veto_signalling_duration = 0
                     self.log.append({'event': 'convert_to_rage_quit','timestamp': events_flow[event_num]['timestamp']})
                     self.log.append({'event': 'rage_quit_end','timestamp': int(events_flow[event_num]['timestamp']+waiting_time+self.rage_quit_extension_delay)})
                     simulation.add_event({'timestamp': int(events_flow[event_num]['timestamp']+waiting_time+self.rage_quit_extension_delay), 'method': 'rage_quit_end','amount':0})

                #Signalling -> deactivation transition
                 if (events_flow[event_num]['timestamp']-self.last_veto_signalling_start >= self.veto_signalling_duration) and \
                        (events_flow[event_num]['timestamp']-max(self.last_veto_signalling_start,self.last_veto_reactivation_start)>self.veto_signalling_min_active_dur) and \
                        (self.current_state=='veto_signalling' or  events_flow[event_num]['method'] == 'rage_quit_end'):
                     self.current_state = 'veto_deactivation'
                     self.log.append({'event':'enter_veto_deactivation','timestamp':events_flow[event_num]['timestamp']})
                     self.last_veto_deactivation_start = events_flow[event_num]['timestamp']
                     simulation.add_event({'timestamp': events_flow[event_num]['timestamp']+self.veto_signalling_deact_max_dur, 'method': 'deactivation_end','amount':0})


                 total_waiting_time=int(self.calculate_veto_signalling_duration(self.total_stETH,self.stETH_in_opposition))
                 #Veto deactivation -> signalling transition
                 if self.current_state == 'veto_deactivation' and (events_flow[event_num]['timestamp']-self.last_veto_signalling_start < total_waiting_time or
                                                            self.stETH_in_opposition / self.total_stETH > self.second_seal_rage_quit ):
                    self.current_state = 'veto_signalling'
                    self.log.append({'event': 'enter_veto_reactivation','timestamp':  events_flow[event_num]['timestamp']})
                    self.last_veto_reactivation_start =  events_flow[event_num]['timestamp']

                 #Deactivation -> cooldown transition
                 if self.current_state == 'veto_deactivation' and events_flow[event_num]['timestamp'] - self.last_veto_deactivation_start >= self.veto_signalling_deact_max_dur:
                    self.current_state = 'veto_cooldown'
                    self.log.append({'event':'enter_veto_cooldown','timestamp': events_flow[event_num]['timestamp']})
                    self.last_veto_cooldown_start =  events_flow[event_num]['timestamp']
                    simulation.add_event({'timestamp': events_flow[event_num]['timestamp']+self.veto_cooldown_duration, 'method': 'cooldown_end','amount':0})

                 #Cooldown -> signalling transition
                 if self.current_state == 'veto_cooldown' and events_flow[event_num]['timestamp']-self.last_veto_cooldown_start >= self.veto_cooldown_duration and \
                        self.stETH_in_opposition/self.total_stETH > self.first_seal_rage_quit :
                    self.veto_signalling_duration=int(self.calculate_veto_signalling_duration(self.total_stETH,self.stETH_in_opposition))
                    self.current_state = 'veto_signalling'
                    self.last_veto_signalling_start = events_flow[event_num]['timestamp']
                    simulation.add_event({'timestamp': events_flow[event_num]['timestamp']+self.veto_signalling_duration, 'method': 'signalling_end','amount':0})
                    self.log.append({'event': 'enter_veto_signalling', 'timestamp': events_flow[event_num]['timestamp']})

                 #Cooldown -> Normal transition
                 if self.current_state == 'veto_cooldown' and  events_flow[event_num]['timestamp']-self.last_veto_cooldown_start >= self.veto_cooldown_duration \
                    and self.stETH_in_opposition/self.total_stETH <= self.first_seal_rage_quit:
                    self.current_state ='normal'
                    self.rage_quit_growth_start_seq_number = 2
                    self.log.append({'event':'enter_normal_state','timestamp':events_flow[event_num]['timestamp']})

                 events_flow=sorted(simulation.events_flow.iloc[day,2], key=lambda x:x['timestamp'])
                 event_num +=1
                 event_amount=len(events_flow)
        
        print('Procesion finished')

    def show_log(self):
        beautiful_log=pd.DataFrame(self.log)
        beautiful_log['end_timestamp']=beautiful_log['timestamp'].shift(-1)
        beautiful_log['waiting_time']=(beautiful_log['end_timestamp']-beautiful_log['timestamp'])/(60*60*24)
        return beautiful_log
    
    def show_total_waiting_time(self):
        waiting_time = self.show_log()['waiting_time'].sum()
        print (f'Total waiting time is {waiting_time:.2f} days')

                 
    def calculate_rage_quit_duration(self,rage_quit, lido_exit_share):
        exit_churn_rate=max(((rage_quit['others_stacked_eth_amount']+rage_quit['stETH_amount'])/32)//2**16,4)
        exit_time=math.ceil(rage_quit['eth_to_exit']/32)/(lido_exit_share*exit_churn_rate)*32*12
        return exit_time

    def calculate_rage_quit_withdraw_timelock(self,rage_quit):
        if rage_quit['seq_number'] < self.rage_quit_growth_start_seq_number:
            return self.rage_quit_eth_claim_min_time_lock
        else:
            additional_time=self.rage_quit_growth_coef[2]*(rage_quit['seq_number']-self.rage_quit_growth_start_seq_number)**2+self.rage_quit_growth_coef[1]*rage_quit['seq_number']+self.rage_quit_growth_coef[0]
            return self.rage_quit_eth_claim_min_time_lock+additional_time
        
    def show_rage_quit_withdraw_timelock(self):
        for rage_quit in range(len(self.rage_quits)):
            timelock=self.calculate_rage_quit_withdraw_timelock(self.rage_quits[rage_quit])
            print(f'Rage quit {rage_quit+1} withdraw timelock is {timelock/(60*60*24):.2f} days')


class simulation:
    def __init__(self,initial_stETH,others_eth_staked,stETH_in_opposition):
        self.initial_stETH = initial_stETH
        self.initial_others_eth_staked = others_eth_staked
        self.initial_stETH_in_opposition = stETH_in_opposition

    def generate_events_flow(self,start_timestamp, end_timestamp):
        date_range = pd.date_range(start=pd.to_datetime(start_timestamp, unit='s'), end=pd.to_datetime(end_timestamp, unit='s'),freq='24h')
        
        date_range_timestamps = date_range.astype(np.int64) // 10**9
        
        data = {
        'start_timestamp': date_range_timestamps[:-1],
        'end_timestamp': date_range_timestamps[1:],
        'event': [[] for _ in range(len(date_range_timestamps) - 1)]
        }   
        
        self.events_flow = pd.DataFrame(data)

    def find_row(self,timestamp):
        try:
            return int(self.events_flow[(self.events_flow['start_timestamp'] <= timestamp) & (self.events_flow['end_timestamp'] >= timestamp)].index[0])
        except IndexError:
            raise IndexError ("Event timestamp are out of simulation bounds")

    
    def change_opposition_stETH_amount(self,amount,timestamp):
        event = {'timestamp':timestamp, 'method':'change_opposition_stETH_amount', 'amount':amount}
        row = self.find_row(timestamp)
        self.events_flow.iloc[row,2].append(event)
        
    
    def change_stETH_amount(self,amount,timestamp):
        event = {'timestamp':timestamp, 'method':'change_stETH_amount', 'amount':amount}
        row = self.find_row(timestamp)
        self.events_flow.iloc[row,2].append(event)
        

    def change_others_staked_eth_amount(self,amount,timestamp):
        event = {'timestamp':timestamp, 'method':'change_others_staked_eth_amount', 'amount':amount}
        row = self.find_row(timestamp)
        self.events_flow.iloc[row,2].append(event)
        
    def add_event(self,event):
        row = self.find_row(event['timestamp'])
        self.events_flow.iloc[row,2].append(event)
    
        



