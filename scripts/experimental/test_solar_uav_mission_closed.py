# test_solar_UAV_mission.py
# 
# Created:  Emilio Botero, July 2014

#----------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------
import sys
sys.path.append('../trunk')


import SUAVE
from SUAVE.Attributes import Units

from SUAVE.Structure import (
Data, Container, Data_Exception, Data_Warning,
)

import numpy as np
import pylab as plt
import matplotlib
import copy, time

from SUAVE.Components.Energy.Networks.Solar_Network import Solar_Network
from SUAVE.Components.Energy.Converters.Propeller_Design import Propeller_Design

# ----------------------------------------------------------------------
#   Main
# ----------------------------------------------------------------------
def main():
    
    weight      = 200.0 #Kg
    weight_last = 0.0 
    delta       = weight - weight_last
    
    while delta > 0.5:
    
        # build the vehicle
        vehicle = define_vehicle(weight)
        
        weight_last = weight
        weight      = vehicle.Mass_Props.mass
        delta       = np.abs(weight - weight_last)
        
    print('Converged Vehicle Weight:')
    print(weight)
    
    # define the mission
    mission = define_mission(vehicle)
    
    # evaluate the mission
    results = evaluate_mission(vehicle,mission)
    
    # plot results
    
    post_process(vehicle,mission,results)
    
    return

# ----------------------------------------------------------------------
#   Build the Vehicle
# ----------------------------------------------------------------------

def define_vehicle(weight):
    
    # ------------------------------------------------------------------
    #   Initialize the Vehicle
    # ------------------------------------------------------------------    
    
    vehicle = SUAVE.Vehicle()
    vehicle.tag = 'Solar'
    vehicle.Propulsors.propulsor = SUAVE.Components.Energy.Networks.Solar_Network()
    
    # ------------------------------------------------------------------
    #   Vehicle-level Properties
    # ------------------------------------------------------------------    
    # mass properties
    vehicle.Mass_Props.m_full    = weight
    vehicle.Mass_Props.m_empty   = weight
    vehicle.Mass_Props.m_takeoff = weight 
    
    # basic parameters
    vehicle.delta         = 0.                # deg
    vehicle.S             = 80.               # m^2
    vehicle.Ultimate_Load = 2.0
    vehicle.qm            = 0.5*1.225*(20.**2.) #Max q
    vehicle.Ltb           = 10.
    
    # ------------------------------------------------------------------        
    #   Main Wing
    # ------------------------------------------------------------------   

    wing = SUAVE.Components.Wings.Wing()
    wing.tag = 'Main Wing'
    
    wing.sref      = vehicle.S     #
    wing.span      = 40.          #m
    wing.ar        = (wing.span**2)/vehicle.S 
    wing.sweep     = vehicle.delta * Units.deg #
    wing.symmetric = True          #
    wing.t_c       = 0.12          #
    wing.taper     = 1             #    
    
    # size the wing planform
    SUAVE.Geometry.Two_Dimensional.Planform.wing_planform(wing)
    
    wing.chord_mac   = wing.sref/wing.span   #
    wing.S_exposed   = 0.8*wing.area_wetted  # might not be needed as input
    wing.S_affected  = 0.6*wing.area_wetted  # part of high lift system
    wing.e           = 0.97                  #
    wing.alpha_rc    = 0.0                   #
    wing.alpha_tc    = 0.0                   #
    wing.twist_rc    = 0.0*Units.degrees     #
    wing.twist_tc    = 0.0*Units.degrees     #  
    wing.highlift    = False     
    wing.Nwr         = 20.
    wing.Nwer        = 2.
    
    # add to vehicle
    vehicle.append_component(wing)
    
    # ------------------------------------------------------------------        
    #  Horizontal Stabilizer
    # ------------------------------------------------------------------        
    
    wing = SUAVE.Components.Wings.Wing()
    wing.tag = 'Horizontal Stabilizer'
    
    wing.sref      = vehicle.S*.15  #m^2
    wing.ar        = 20            #
    wing.span      = np.sqrt(wing.ar*wing.sref)
    wing.sweep     = 0 * Units.deg              #
    wing.symmetric = True          
    wing.t_c       = 0.12                       #
    wing.taper     = 1                          #
    wing.twist_rc  = 0.0*Units.degrees     #
    wing.twist_tc  = 0.0*Units.degrees     #      
    
    # size the wing planform
    SUAVE.Geometry.Two_Dimensional.Planform.wing_planform(wing)
    
    wing.chord_mac  = wing.sref/wing.span
    wing.S_exposed  = 0.8*wing.area_wetted  #
    wing.S_affected = 0.6*wing.area_wetted  #      
    wing.e          = 0.95                   #
    wing.alpha_rc   = 0.                   #
    wing.alpha_tc   = 0.                   #
    wing.Nwr        = 5.
  
    # add to vehicle
    vehicle.append_component(wing)    
    
    # ------------------------------------------------------------------
    #   Vertical Stabilizer
    # ------------------------------------------------------------------
    
    wing = SUAVE.Components.Wings.Wing()
    wing.tag = 'Vertical Stabilizer'    
    
    wing.sref      = vehicle.S*.1 #m^2
    wing.ar        = 20             #
    wing.span      = np.sqrt(wing.ar*wing.sref)
    wing.sweep     = 0 * Units.deg              #
    wing.symmetric = True          
    wing.t_c       = 0.12                       #
    wing.taper     = 1                          #
    wing.twist_rc  = 0.0*Units.degrees     #
    wing.twist_tc  = 0.0*Units.degrees     #          
    
    # size the wing planform
    SUAVE.Geometry.Two_Dimensional.Planform.wing_planform(wing)
    
    wing.chord_mac  = wing.sref/wing.span
    wing.S_exposed  = 0.8*wing.area_wetted  #
    wing.S_affected = 0.6*wing.area_wetted  #      
    wing.e          = 0.95                  #
    wing.alpha_rc   = 0.                    #
    wing.alpha_tc   = 0.                    #
    wing.Nwr        = 5.
  
    # add to vehicle
    vehicle.append_component(wing)  
    
    # ------------------------------------------------------------------
    #   Propulsor
    # ------------------------------------------------------------------
    
    #Propeller design point
    design_altitude = 23.0 * Units.km
    Velocity        = 50.0 # freestream m/s
    RPM             = 5000.
    Blades          = 2.0
    Radius          = 1.5
    Hub_Radius      = 0.0508
    Thrust          = 0.0     #Specify either thrust or power to design for
    Power           = 10000.0 #Specify either thrust or power to design for
    
    atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()
    p, T, rho, a, mu = atmosphere.compute_values(design_altitude)
    
    #Design the Propeller
    Prop_attributes        = Data()
    Prop_attributes.nu     = mu/rho
    Prop_attributes.B      = Blades 
    Prop_attributes.V      = Velocity
    Prop_attributes.omega  = RPM*(2.*np.pi/60.0)
    Prop_attributes.R      = Radius
    Prop_attributes.Rh     = Hub_Radius
    Prop_attributes.Des_CL = 0.7
    Prop_attributes.rho    = rho
    Prop_attributes.Tc     = 2.*Thrust/(rho*(Velocity**2.)*np.pi*(Radius**2.))
    Prop_attributes.Pc     = 2.*Power/(rho*(Velocity**3.)*np.pi*(Radius**2.))
    Prop_attributes        = Propeller_Design(Prop_attributes)
    
    # build network
    net             = Solar_Network()
    net.num_motors  = 1.
    net.nacelle_dia = 0.2
    
    # Component 1 the Sun?
    sun            = SUAVE.Components.Energy.Properties.solar()
    net.solar_flux = sun
    
    # Component 2 the solar panels
    panel                 = SUAVE.Components.Energy.Converters.Solar_Panel()
    panel.A               = vehicle.S + vehicle.Wings['Horizontal Stabilizer'].sref
    panel.eff             = 0.22
    panel.Mass_Props.mass = panel.A*.550
    net.solar_panel       = panel
    
    # Component 3 the ESC
    esc     = SUAVE.Components.Energy.Distributors.ESC()
    esc.eff = 0.95 # Gundlach for brushless motors
    net.esc = esc
    
    # Component 5 the Propeller
    prop                 = SUAVE.Components.Energy.Converters.Propeller()
    prop.Prop_attributes = Prop_attributes
    net.propeller        = prop

    # Component 4 the Motor
    motor     = SUAVE.Components.Energy.Converters.Motor()
    motor.Res             = 0.008
    motor.io              = 4.5
    motor.kv              = 120.*(2.*np.pi/60.) # RPM/volt converted to rad/s     
    motor.propradius      = prop.Prop_attributes.R
    motor.propCp          = prop.Prop_attributes.Cp
    motor.G               = 1. # Gear ratio
    motor.etaG            = 1. # Gear box efficiency
    motor.exp_i           = 160. # Expected current
    motor.Mass_Props.mass = 2.0
    net.motor             = motor    
    
    # Component 6 the Payload
    payload                 = SUAVE.Components.Energy.Peripherals.Payload()
    payload.draw            = 250. #Watts 
    payload.Mass_Props.mass = 25.0 * Units.kg
    net.payload             = payload
    
    # Component 7 the Avionics
    avionics      = SUAVE.Components.Energy.Peripherals.Avionics()
    avionics.draw = 25. #Watts  
    net.avionics  = avionics
    
    # Component 8 the Battery
    bat                 = SUAVE.Components.Energy.Storages.Battery()
    bat.Mass_Props.mass = 83.  #kg
    bat.type            = 'Li-Ion'
    bat.R0              = 0.07
    net.battery         = bat
   
    #Component 9 the system logic controller and MPPT
    logic               = SUAVE.Components.Energy.Distributors.Solar_Logic()
    logic.systemvoltage = 65.0
    logic.MPPTeff       = 0.95
    net.solar_logic     = logic
    
    vehicle.Mass_Props.breakdown = SUAVE.Methods.Weights.Correlations.Solar_HPA.empty(vehicle)
    
    # ------------------------------------------------------------------
    #   Simple Aerodynamics Model
    # ------------------------------------------------------------------ 
    
    aerodynamics = SUAVE.Attributes.Aerodynamics.Fidelity_Zero()
    aerodynamics.initialize(vehicle)
    vehicle.aerodynamics_model = aerodynamics
    
    # ------------------------------------------------------------------
    #   Not so Simple Propulsion Model
    # ------------------------------------------------------------------ 
    vehicle.propulsion_model = net
    
    # ------------------------------------------------------------------
    #   Define Configurations
    # ------------------------------------------------------------------
    
    # --- Takeoff Configuration ---
    config = vehicle.new_configuration("takeoff")
    # this configuration is derived from the baseline vehicle

    # --- Cruise Configuration ---
    config = vehicle.new_configuration("cruise")
    # this configuration is derived from vehicle.Configs.takeoff
    
    # ------------------------------------------------------------------
    #   Add up all of the masses
    # ------------------------------------------------------------------
    wingmass  = vehicle.Wings['Main Wing'].Mass_Props.mass
    HTmass    = vehicle.Wings['Horizontal Stabilizer'].Mass_Props.mass
    VTmass    = vehicle.Wings['Vertical Stabilizer'].Mass_Props.mass
    batmass   = bat.Mass_Props.mass
    motmass   = motor.Mass_Props.mass
    paylmass  = payload.Mass_Props.mass
    panelmass = panel.Mass_Props.mass
    
    total_mass = (wingmass + HTmass + VTmass + batmass +
                  motmass + paylmass + panelmass)
    
    vehicle.Mass_Props.mass = total_mass

    # ------------------------------------------------------------------
    #   Vehicle Definition Complete
    # ------------------------------------------------------------------
    
    
    return vehicle

# ----------------------------------------------------------------------
#   Define the Mission
# ----------------------------------------------------------------------
def define_mission(vehicle):
    
    # ------------------------------------------------------------------
    #   Initialize the Mission
    # ------------------------------------------------------------------

    mission = SUAVE.Attributes.Missions.Mission()
    mission.tag = 'The Test Mission'

    # initial mass
    mission.m0 = vehicle.Mass_Props.m_full # linked copy updates if parent changes
    
    # atmospheric model
    atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()
    planet     = SUAVE.Attributes.Planets.Earth()
    
    # ------------------------------------------------------------------
    #   Climb Segment: Constant Speed, constant throttle
    # ------------------------------------------------------------------
    
    segment = SUAVE.Attributes.Missions.Segments.Climb.Constant_Throttle_Constant_Speed()
    segment.tag = "Climb 1"
    
    # connect vehicle configuration
    segment.config = vehicle.Configs.takeoff
    
    # define segment attributes
    segment.atmosphere     = atmosphere
    segment.planet         = planet    
    
    segment.altitude_start = 14.0   * Units.km
    segment.altitude_end   = 18.0   * Units.km
    segment.air_speed      = 30.0  * Units['m/s']
    segment.throttle       = 0.55
    segment.battery_energy = vehicle.propulsion_model.battery.max_energy() #Charge the battery to start
    
    # add to misison
    mission.append_segment(segment)
    
    # ------------------------------------------------------------------
    #   Second Climb Segment: Constant Speed, constant rate
    # ------------------------------------------------------------------    
    
    segment = SUAVE.Attributes.Missions.Segments.Climb.Constant_Speed_Constant_Rate()
    segment.tag = "Climb - 2"
    
    # connect vehicle configuration
    segment.config = vehicle.Configs.cruise
    
    # segment attributes
    segment.atmosphere     = atmosphere
    segment.planet         = planet    
    
    segment.altitude_start = 18.0   * Units.km # Optional
    segment.altitude_end   = 24.0   * Units.km
    segment.air_speed      = 40.0  * Units['m/s']
    segment.climb_rate     = 0.75   * Units['m/s']

    # add to mission
    mission.append_segment(segment)
    
    # ------------------------------------------------------------------
    #   Second Climb Segment: Constant Speed, constant rate
    # ------------------------------------------------------------------    
    
    segment = SUAVE.Attributes.Missions.Segments.Climb.Constant_Speed_Constant_Rate()
    segment.tag = "Climb - 3"
    
    # connect vehicle configuration
    segment.config = vehicle.Configs.cruise
    
    # segment attributes
    segment.atmosphere     = atmosphere
    segment.planet         = planet    
    
    segment.altitude_start = 24.0   * Units.km # Optional
    segment.altitude_end   = 28.0   * Units.km
    segment.air_speed      = 50.0   * Units['m/s']
    segment.climb_rate     = 0.25   * Units['m/s']

    # add to mission
    mission.append_segment(segment)
    
    
    # ------------------------------------------------------------------    
    #   Cruise Segment: constant speed, constant altitude
    # ------------------------------------------------------------------    
    
    segment = SUAVE.Attributes.Missions.Segments.Cruise.Constant_Speed_Constant_Altitude()
    segment.tag = "Cruise"
    
    # connect vehicle configuration
    segment.config = vehicle.Configs.cruise
    
    # segment attributes
    segment.atmosphere = atmosphere
    segment.planet     = planet        
    
    segment.altitude   = 28.0  * Units.km     # Optional
    segment.air_speed  = 50.0  * Units['m/s']
    segment.distance   = 1000.0 * Units.km
        
    mission.append_segment(segment)

    # ------------------------------------------------------------------    
    #   First Descent Segment: constant speed, constant segment rate
    # ------------------------------------------------------------------    

    segment = SUAVE.Attributes.Missions.Segments.Descent.Constant_Speed_Constant_Rate()
    segment.tag = "Descent - 1"
    
    # connect vehicle configuration
    segment.config = vehicle.Configs.cruise
    
    # segment attributes
    segment.atmosphere   = atmosphere
    segment.planet       = planet   
    
    segment.altitude_end = 18.  * Units.km
    segment.air_speed    = 50.0 * Units['m/s']
    segment.descent_rate = 0.6  * Units['m/s']
    
    # add to mission
    mission.append_segment(segment) 

    # ------------------------------------------------------------------    
    #   Mission definition complete    
    # ------------------------------------------------------------------
    
    return mission

# ----------------------------------------------------------------------
#   Evaluate the Mission
# ----------------------------------------------------------------------
def evaluate_mission(vehicle,mission):
    
    # ------------------------------------------------------------------    
    #   Run Mission
    # ------------------------------------------------------------------
    results = SUAVE.Methods.Performance.evaluate_mission(mission)
    
    return results

# ----------------------------------------------------------------------
#   Plot Results
# ----------------------------------------------------------------------
def post_process(vehicle,mission,results):

    # ------------------------------------------------------------------    
    #   Throttle
    # ------------------------------------------------------------------
    plt.figure("Throttle History")
    axes = plt.gca()
    for i in range(len(results.Segments)):
        time = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        eta  = results.Segments[i].conditions.propulsion.throttle[:,0]
        
        axes.plot(time, eta, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Throttle')
    axes.grid(True)
    
    plt.figure("Angle of Attack History")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        aoa = results.Segments[i].conditions.aerodynamics.angle_of_attack[:,0] / Units.deg
        axes.plot(time, aoa, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Angle of Attack (deg)')
    axes.grid(True)            

    # ------------------------------------------------------------------    
    #   Altitude
    # ------------------------------------------------------------------
    plt.figure("Altitude")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        altitude = results.Segments[i].conditions.freestream.altitude[:,0] / Units.km
        axes.plot(time, altitude, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Altitude (km)')
    axes.grid(True)    
    
    # ------------------------------------------------------------------    
    #   Aerodynamics
    # ------------------------------------------------------------------
    fig = plt.figure("Aerodynamic Forces")
    for segment in results.Segments.values():
        
        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        Lift   = -segment.conditions.frames.wind.lift_force_vector[:,2]
        Drag   = -segment.conditions.frames.wind.drag_force_vector[:,0]
        Thrust = segment.conditions.frames.body.thrust_force_vector[:,0]

        axes = fig.add_subplot(3,1,1)
        axes.plot( time , Lift , 'bo-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('Lift (N)')
        axes.grid(True)
        
        axes = fig.add_subplot(3,1,2)
        axes.plot( time , Drag , 'bo-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('Drag (N)')
        axes.grid(True)
        
        axes = fig.add_subplot(3,1,3)
        axes.plot( time , Thrust , 'bo-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('Thrust (N)')
        axes.grid(True)
        
    # ------------------------------------------------------------------    
    #   Aerodynamics 2
    # ------------------------------------------------------------------
    fig = plt.figure("Aerodynamic Coefficients")
    for segment in results.Segments.values():
        
        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        CLift  = segment.conditions.aerodynamics.lift_coefficient[:,0]
        CDrag  = segment.conditions.aerodynamics.drag_coefficient[:,0]
        Drag   = -segment.conditions.frames.wind.drag_force_vector[:,0]
        Thrust = segment.conditions.frames.body.thrust_force_vector[:,0]

        axes = fig.add_subplot(3,1,1)
        axes.plot( time , CLift , 'bo-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('CL')
        axes.grid(True)
        
        axes = fig.add_subplot(3,1,2)
        axes.plot( time , CDrag , 'bo-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('CD')
        axes.grid(True)
        
        axes = fig.add_subplot(3,1,3)
        axes.plot( time , Drag   , 'bo-' )
        axes.plot( time , Thrust , 'ro-' )
        axes.set_xlabel('Time (min)')
        axes.set_ylabel('Drag and Thrust (N)')
        axes.grid(True)
        
    
    # ------------------------------------------------------------------    
    #   Aerodynamics 2
    # ------------------------------------------------------------------
    fig = plt.figure("Drag Components")
    axes = plt.gca()    
    for i, segment in enumerate(results.Segments.values()):
        
        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        drag_breakdown = segment.conditions.aerodynamics.drag_breakdown
        cdp = drag_breakdown.parasite.total[:,0]
        cdi = drag_breakdown.induced.total[:,0]
        cdc = drag_breakdown.compressible.total[:,0]
        cdm = drag_breakdown.miscellaneous.total[:,0]
        cd  = drag_breakdown.total[:,0]
        
        
        axes.plot( time , cdp , 'ko-', label='CD_P' )
        axes.plot( time , cdi , 'bo-', label='CD_I' )
        axes.plot( time , cdc , 'go-', label='CD_C' )
        axes.plot( time , cdm , 'yo-', label='CD_M' )
        axes.plot( time , cd  , 'ro-', label='CD'   )
        
        if i == 0:
            axes.legend(loc='upper center')
        
    axes.set_xlabel('Time (min)')
    axes.set_ylabel('C_D')
    axes.grid(True)
    
    
    # ------------------------------------------------------------------    
    #   Battery Energy
    # ------------------------------------------------------------------
    plt.figure("Battery Energy")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        energy = results.Segments[i].conditions.propulsion.battery_energy[:,0] 
        axes.plot(time, energy, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Battery Energy (J)')
    axes.grid(True)   
    
    # ------------------------------------------------------------------    
    #   Solar Flux
    # ------------------------------------------------------------------
    plt.figure("Solar Flux")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        energy = results.Segments[i].conditions.propulsion.solar_flux[:,0] 
        axes.plot(time, energy, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Solar Flux ($W/m^{2}$)')
    axes.grid(True)      
    
    # ------------------------------------------------------------------    
    #   Current Draw
    # ------------------------------------------------------------------
    plt.figure("Current Draw")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        energy = results.Segments[i].conditions.propulsion.current[:,0] 
        axes.plot(time, energy, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Current Draw (Amps)')
    axes.grid(True)  
    
    # ------------------------------------------------------------------    
    #   Motor RPM
    # ------------------------------------------------------------------
    plt.figure("Motor RPM")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        energy = results.Segments[i].conditions.propulsion.rpm[:,0] 
        axes.plot(time, energy, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Motor RPM')
    axes.grid(True)
    
    # ------------------------------------------------------------------    
    #   Battery Draw
    # ------------------------------------------------------------------
    plt.figure("Battery Charging")
    axes = plt.gca()    
    for i in range(len(results.Segments)):     
        time     = results.Segments[i].conditions.frames.inertial.time[:,0] / Units.min
        energy = results.Segments[i].conditions.propulsion.battery_draw[:,0] 
        axes.plot(time, energy, 'bo-')
    axes.set_xlabel('Time (mins)')
    axes.set_ylabel('Battery Charging (Watts)')
    axes.grid(True)      
    
    
    plt.show()     
    
    return     

# ---------------------------------------------------------------------- 
#   Module Tests
# ----------------------------------------------------------------------

if __name__ == '__main__':
    
    profile_module = False
        
    if not profile_module:
        main()
        
    else:
        profile_file = 'log_Profile.out'
        
        import cProfile
        cProfile.run('import tut_mission_Boeing_737800 as tut; tut.profile()', profile_file)
        
        import pstats
        p = pstats.Stats(profile_file)
        p.sort_stats('time').print_stats(20)        
        
        import os
        os.remove(profile_file)

def profile():
    t0 = time.time()
    vehicle = define_vehicle()
    mission = define_mission(vehicle)
    results = evaluate_mission(vehicle,mission)
    print 'Run Time:' , (time.time()-t0)    