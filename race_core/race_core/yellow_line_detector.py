#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Vector3
from cv_bridge import CvBridge
import cv2
import numpy as np
from rclpy.qos import qos_profile_sensor_data

class YellowLineDetector(Node):
    def __init__(self):
        super().__init__('yellow_line_detector')
        self.sub_img = self.create_subscription(
            Image, '/cyberdog_camera/image_raw', self.img_callback, qos_profile_sensor_data)
        self.pub_line = self.create_publisher(Vector3, '/perception/yellow_line', 10)
        self.bridge = CvBridge()
        self.get_logger().info("🟡 远近场差分视觉组件 (自动驾驶级) 启动！")

    def get_center(self, mask_region, full_w):
        """寻找区域内双线或单线的几何中心"""
        contours, _ = cv2.findContours(mask_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x_centers = []
        for c in contours:
            if cv2.contourArea(c) > 100: # 过滤极小噪点
                x, y, w, h = cv2.boundingRect(c)
                x_centers.append(x + w/2.0)
        
        if len(x_centers) >= 2:
            x_centers.sort()
            return (x_centers[0] + x_centers[-1]) / 2.0  # 双线中点
        elif len(x_centers) == 1:
            single_x = x_centers[0]
            lane_w = full_w * 0.6
            # 单线猜测补偿
            return single_x + lane_w/2.0 if single_x < full_w/2.0 else single_x - lane_w/2.0
        return None

    def img_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            h, w, _ = cv_image.shape
            
            roi = cv_image[int(h/2):h, :].copy()
            roi_h, roi_w, _ = roi.shape
            
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))

            # 🌟【第一性原理】：将视野切分为远近两部分
            # 近场 (脚下) - 用于极其稳定的直道巡线
            near_mask = mask[int(roi_h*0.6):roi_h, :]
            # 远场 (前方) - 用于提前预判急转弯
            far_mask = mask[0:int(roi_h*0.4), :]

            near_cx = self.get_center(near_mask, roi_w)
            far_cx = self.get_center(far_mask, roi_w)

            out_msg = Vector3()
            out_msg.y = 0.0  # 0代表直走，1代表急右转，-1代表急左转
            out_msg.z = 0.0  # 状态标志

            if near_cx is not None:
                out_msg.z = 1.0
                # 归一化近场误差 (-1.0 到 1.0)
                out_msg.x = (near_cx - (roi_w / 2.0)) / (roi_w / 2.0)
                
                # 画出近场基准点 (绿色)
                cv2.circle(roi, (int(near_cx), int(roi_h*0.8)), 8, (0, 255, 0), -1)

                # 🌟 直角弯检测逻辑：对比远近场
                if far_cx is not None:
                    # 画出远场预测点 (蓝色)
                    cv2.circle(roi, (int(far_cx), int(roi_h*0.2)), 8, (255, 0, 0), -1)
                    
                    # 远方中心点相比于脚下中心点，发生剧烈横移 (> 屏幕宽度的 25%)
                    shift = far_cx - near_cx
                    if shift > roi_w * 0.25:
                        out_msg.y = 1.0 # 右方有直角弯！
                        cv2.putText(roi, "CORNER RIGHT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    elif shift < -roi_w * 0.25:
                        out_msg.y = -1.0 # 左方有直角弯！
                        cv2.putText(roi, "CORNER LEFT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            
            else:
                # 脚下完全看不到线 (彻底丢失)
                out_msg.x = 0.0
                out_msg.z = 0.0

            self.pub_line.publish(out_msg)
            cv2.imshow("Advanced Far-Near Tracker", roi)
            cv2.waitKey(1)
            
        except Exception as e:
            self.get_logger().error(f"视觉崩溃: {e}")

def main():
    rclpy.init()
    node = YellowLineDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()