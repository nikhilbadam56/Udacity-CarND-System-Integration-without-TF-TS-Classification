#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
from scipy.spatial import KDTree
import math
import numpy as np

from std_msgs.msg import Int32
MAX_DECEL = .5

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number


class WaypointUpdater(object):
    
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below


        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)
        rospy.Subscriber('/traffic_waypoint',Int32,self.traffic_cb)

        # TODO: Add other member variables you need below
        
        self.base_waypoints = None
        
        self.waypoints_2d = None
        
        self.waypoint_tree = None
        
        self.pose = None

        self.sp_line_indx = None


        self.loop()
        
    def loop(self):
        
        rate = rospy.Rate(10)
        
        while not rospy.is_shutdown():
            
            
            if self.pose is not None :
                if self.base_waypoints is not None:

                    if self.waypoint_tree is not None:
                
                        #get closes_waypoint_idx
                        self.puslish_waypoints()
                
            rate.sleep()
    def get_closest_waypoints(self):
        
        x = self.pose.pose.position.x
        y = self.pose.pose.position.y
        
        closest_idx = self.waypoint_tree.query([x,y],1)[1]
        
        #checking for the relative position of teh way points with respect to the position of the car COG
        closest_coord =  self.waypoints_2d[closest_idx]
        prev_coord = self.waypoints_2d[closest_idx-1]
        
        cl_vect = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect = np.array([x,y])
        
        val = np.dot(cl_vect - prev_vect , pos_vect - cl_vect)
        
        if val>0:
            closest_idx = (closest_idx + 1)%len(self.waypoints_2d)
        return closest_idx
    
    def puslish_waypoints(self):
        
        # lane  = Lane()
        # lane.header = self.base_waypoints.header
        # closes_idx = self.get_closest_waypoints()
        # lane.waypoints = self.base_waypoints.waypoints[closes_idx:closes_idx+LOOKAHEAD_WPS]
        # print(self.final_waypoints_pub.publish(lane))
        if self.sp_line_indx is not None:
            lane = self.generate_lane()
            self.final_waypoints_pub.publish(lane)
        
    def generate_lane(self):
        lane = Lane()
        
        closest_idx = self.get_closest_waypoints()
        farthest_idx = closest_idx + LOOKAHEAD_WPS
        base_way = self.base_waypoints.waypoints[closest_idx:farthest_idx]
        if self.sp_line_indx == -1 or (self.sp_line_indx >= farthest_idx):
            lane.waypoints = base_way
        else:
            lane.waypoints = self.deccelerate_waypoints(base_way,closest_idx)
        return lane
    def deccelerate_waypoints(self,base_way,closest_idx):
        
        temp = []
        for i,wp in enumerate(base_way):
            p = Waypoint()
            p.pose = wp.pose
            
            stop_idx = max(self.sp_line_indx - closest_idx - 2,0)
            
            dist = self.distance(base_way,i,stop_idx)
            
            vel = math.sqrt(2*MAX_DECEL*dist)
            if vel<1.:
                vel = 0.
            
            p.twist.twist.linear.x = min(vel,wp.twist.twist.linear.x)
            temp.append(p)
        return temp
            
    def pose_cb(self, msg):
        # TODO: Implement
        self.pose = msg

    def waypoints_cb(self, waypoints):
        # TODO: Implemens
        self.base_waypoints = waypoints #caching the waypoints 
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x,waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d) #for finding the nearest waypoint

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        self.sp_line_indx = msg.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
