from yaw_controller import YawController
from pid import PID
import rospy
from lowpass import LowPassFilter
GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self,vehicle_mass,fuel_capacity,brake_deadband,decel_limit,accel_limit,wheel_radius,wheel_base,steer_ration,max_lat_accel,max_steer_angle):
        # TODO: Implement
        self.yaw_controller = YawController(wheel_base,steer_ration,0.1,max_lat_accel,max_steer_angle)
        
        #parameter values
        kp = 0.3
        ki = 0.1
        kd = 0.
        mn = 0. #minimum throttle
        mx = 0.2 #maximum throtle
        self.throttle_controller = PID(kp,ki,kd,mn,mx)
        
        tau = 0.5 #cutoff frequency for the LPF
        ts = .02 #sampling time
        
        self.vel_lpf = LowPassFilter(tau,ts)
        
        self.vehicle_mass = vehicle_mass
        self.fuel_capacity = fuel_capacity
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.wheel_radius = wheel_radius
        self.last_vel = None
        self.last_time = rospy.get_time()
        
    def control(self, current_vel,dbw_enabled,linear_vel,angular_vel):
        # TODO: Change the arg, kwarg list to suit your needs
        # Return throttle, brake, steer
        
        if not dbw_enabled: #manual mode or not
            self.throttle_controller.reset()
            return 0.,0.,0.
        current_velocity = self.vel_lpf.filt(current_vel)
        
        steering = self.yaw_controller.get_steering(linear_vel,angular_vel,current_vel)
        
        vel_err = linear_vel  - current_vel
        self.last_vel = current_vel
        
        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time
        
        throttle = self.throttle_controller.step(vel_err,sample_time)
        
        brake = 0
        if linear_vel == 0. and current_vel<0.1:
            throttle = 0
            brake = 700 
        elif throttle < .1 and vel_err<0:
            throttle = 0
            decel = max(vel_err,self.decel_limit)
            brake = abs(decel) * self.vehicle_mass*self.wheel_radius
        return throttle,brake,steering