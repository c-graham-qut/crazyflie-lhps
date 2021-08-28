"""
Original Example by Bitcraze.

This example has been modified to include an emergency stop (esc). 

This script causes the drones to:

1. Take off
2. Hover for 10s
3. Fly 1m positive y (Forward)
4. Hover for 10s
5. Land

This example is intended to work with any absolute positioning system however
testing was done solely with the Lighthouse Positioning System.
"""
import time

import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncLogger import SyncLogger

from pynput import keyboard


def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("{} {} {}".
            #       format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                break


def reset_estimator(scf):
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    wait_for_position_estimator(scf)


def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')


def activate_mellinger_controller(scf, use_mellinger):
    controller = 1
    if use_mellinger:
        controller = 2
    scf.cf.param.set_value('stabilizer.controller', controller)


def run_shared_sequence(scf):
    activate_mellinger_controller(scf, False)

    box_size = 0.5
    flight_time = 3

    commander = scf.cf.high_level_commander

    # Emergency Stop (esc)
    def on_press(key): 
        if key == keyboard.Key.esc:
            commander.stop()
            scf.cf.param.set_value('commander.enHighLevel', '0')
            print('Emergency Stopped ' + str(scf._link_uri))

    with keyboard.Listener(on_press=on_press) as listener: # Each thread has a listener
        # Takeoff
        commander.takeoff(1.0, 2.0)
        time.sleep(10)

        # Forwards
        commander.go_to(1, 0, 0, 0, flight_time, relative=True)
        time.sleep(flight_time + 10)
        
        # Land
        commander.land(0.0, 2.0)
        time.sleep(3)

    listener.join()

    commander.stop()    


# Drone URIs
uris = {
    #'radio://0/60/2M/E7E7E7E7E7',
    #'radio://0/80/2M/E7E7E7E7E7',
    'radio://1/100/2M/E7E7E7E7E7',
    #'radio://1/120/2M/E7E7E7E7E7',
    # Add more URIs if you want more copters in the swarm
}

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        try:
            swarm.parallel_safe(activate_high_level_commander)
            swarm.parallel_safe(reset_estimator)
            swarm.parallel_safe(run_shared_sequence)
        except:
            pass

    print('Program ended...')