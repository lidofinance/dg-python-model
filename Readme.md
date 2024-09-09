## Description  
This model allows to simulate the behaviour of users who participate in Dual Governance. The main purpose of the model is to check which stages Dual Governance will go through, as well as how long these stages will last under different external circumstances. 

## General info   
Two main concepts within this model are DG_model and simulation. The simulation class is responsible for external events (change of stETH, change of stETH in opposition, change in others staked ETH), while the DG_model class is responsible for simulating dual governance contracts. All transition clauses  between stages are hard coded, but the user can change all parameters of Dual Governance (more on parameters and transition [clauses here](https://github.com/lidofinance/dual-governance/blob/develop/docs/mechanism.md))

## How to work with it 
You can find the example  of usage in 'DG-modeling.ipynb' file. 
**First step** : Define DG_model class object.  

   ```
DG_instance_1=DG.DG_instance(  
    SignallingEscrowMinLockTime=5*60*60,  
    ProposalExecutionMinTimelock=3*24*60*60,  
    FirstSealRageQuitSupport=0.01,  
    SecondSealRageQuitSupport=0.1,  
    VetoSignallingDeactivationMaxDuration=3*24*60*60,  
    DynamicTimelockMinDuration=5*24*60*60,  
    DynamicTimelockMaxDuration=45*24*60*60,  
    VetoSignallingMinActiveDuration=5*60*60,  
    RageQuitExtensionDelay=7*24*60*60,  
    RageQuitEthClaimMinTimelock=60*24*60*60,  
    RageQuitEthClaimTimelockGrowthStartSeqNumber=0,  
    RageQuitEthClaimTimelockGrowthCoeffs=[0,1,86400*2],  
    VetoCooldownDuration=5*60*60  
)
   ```
This is an example of an object with parameters equal to pending parameters from specification. Since the model works with timestamp every time unit is converted into seconds. 

**Second step**: Set up a simulation with initial parameters, which include the initial amount of stETH, the initial amount of others staked ETH and the initial amount of stETH in opposition.

    happy_path=DG.simulation(initial_steth,initial_others_staked_eth,initial_steth_in_opposition)

Next add range for your simulation (for how many "days" simulation should work), where the first argument is the start timestamp of a simulation and the second argument is the end timestamp of a simulation.

    happy_path.generate_events_flow(1722638400,1723156800+86400*365)
    
Once again, the model works with seconds,  to make 365 days, you should multiply 86400 (amount of seconds in day) by 365.

When you should add events to your simulation. There are 3 kinds of events:
 - Change in stETH amount
- Change in opposition stETH amount
- Change in other staked ETH amount 

Every change could be positive or negative.

To add an event to the simulation use one of these functions, depending on what kind of event you want to pass to the simulation:

    change_stETH_amount()
    change_opposition_stETH_amount()
    change_others_staked_eth_amount()

Each function takes the amount as the first argument and the timestamp as the second argument. Timestamp represent a time when changes were made. 

Let's add this event to our example

    happy_path.change_opposition_stETH_amount(70000,1722638570)
    happy_path.change_opposition_stETH_amount(50000,1722639670)
    happy_path.change_opposition_stETH_amount(130000,1722718680)
    happy_path.change_opposition_stETH_amount(-250000,1723666372)

The last part is to process the simulation with an established DG_model using the process_simulation  method and use show_log, to display what stages Dual Governance go through and how long did they last:
*Input:*

DG_instance_1.process_simulation(happy_path)
DG_instance_1.show_log()

*Output:*

| event | timestamp | end_timestamp| waiting_time
|--|--|--|--|
| enter_veto_signalling | 1722639670 |1723666370 | 11.88
| enter_veto_deactivation | 1723666370 |1723925570 | 3
| enter_veto_cooldown | 1723925570 | 1723943570| 0.21
| enter_normal_state | 1723943570 |NaN | NaN

In 'DG-modeling.ipynb'  you can find other examples of usage.

**Important note**
If your simulation does not assume rage quit don't forget to extract opposition stETH with this method:

    simulation.change_opposition_stETH_amount(-250000,1723666372)
Otherwise, you would fall into an infinite loop of signalling -> deactivation->cooldown.
It is not a bug, this is a way how dual Governance works

