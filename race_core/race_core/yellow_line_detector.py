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
        
        self.has_turned = False 
        self.get_logger().info("🟡 第一性原理视觉：深度门控 + 巨型蓝球判定 启动！")

    def get_center(self, mask_region, full_w):
        """纯粹用于底部的双线中心点结算"""
        contours, _ = cv2.findContours(mask_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x_centers = []
        for c in contours:
            if cv2.contourArea(c) > 100: 
                x, y, w, h = cv2.boundingRect(c)
                x_centers.append(x + w/2.0)
        
        if len(x_centers) >= 2:
            x_centers.sort()
            return (x_centers[0] + x_centers[-1]) / 2.0  
        elif len(x_centers) == 1:
            single_x = x_centers[0]
            lane_w = full_w * 0.6
            return single_x + lane_w/2.0 if single_x < full_w/2.0 else single_x - lane_w/2.0
        return None

    def img_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            h, w, _ = cv_image.shape
            
            # ====================================================
            # 1. 蓝球检测 (防误判升级版)
            # ====================================================
            saw_blue_ball = False
            if self.has_turned:
                hsv_full = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
                lower_blue = np.array([85, 100, 100])
                upper_blue = np.array([115, 255, 255])
                mask_blue = cv2.inRange(hsv_full, lower_blue, upper_blue)
                
                contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c_blue in contours_blue:
                    # 🌟【第一性原理：体积过滤】
                    # 之前 100 太小了，远处的噪点会误触。现在必须大于 1500 像素！
                    if cv2.contourArea(c_blue) > 7000: 
                        saw_blue_ball = True
                        bx, by, bw, bh = cv2.boundingRect(c_blue)
                        cv2.rectangle(cv_image, (bx, by), (bx+bw, by+bh), (255, 0, 0), 4)
                        cv2.putText(cv_image, "EXIT BALL LOCKED", (bx, by-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 2)
                        break

            out_msg = Vector3()
            out_msg.y = 0.0  
            out_msg.z = 0.0  

            if saw_blue_ball:
                out_msg.z = 2.0
                self.pub_line.publish(out_msg)
                cv2.imshow("Advanced Far-Near Tracker", cv_image)
                cv2.waitKey(1)
                return

            # ====================================================
            # 2. 黄线分析与【深度门控】急弯检测
            # ====================================================
            roi = cv_image[int(h/2):h, :].copy()
            roi_h, roi_w, _ = roi.shape
            
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            turn_triggered = False
            
            for c in contours:
                if cv2.contourArea(c) > 200:
                    x, y, bw, bh = cv2.boundingRect(c)
                    
                    # 判定条件1：是横向线 (宽度远大于高度，且占屏幕宽度的 30% 以上)
                    if bw > bh * 1.5 and bw > roi_w * 0.5:
                        
                        # 🌟【第一性原理：深度门控】
                        # 如果这根横线在 ROI 的上半部 (y 比较小，意味着离狗还很远)
                        if y < roi_h * 0.5:
                            # 只画黄框预警，绝对不发转弯指令！狗会继续笔直往前走！
                            cv2.rectangle(roi, (x, y), (x+bw, y+bh), (0, 255, 255), 2)
                            cv2.putText(roi, "TOO FAR: KEEP GOING", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
                            continue 
                        
                        # 只有横线来到狗脚下 (y >= roi_h * 0.55)，才开始判断左右空白！
                        turn_triggered = True
                        self.has_turned = True
                        
                        # 切分这根线的左右区域，算面积
                        left_area = np.sum(mask[y:y+bh, 0:int(roi_w/3)] > 0)
                        right_area = np.sum(mask[y:y+bh, int(roi_w*2/3):roi_w] > 0)
                        
                        if right_area < left_area * 0.2:
                            out_msg.y = -1.0 # 强制左转
                            cv2.putText(roi, "CLOSE! TURN LEFT", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 3)
                            cv2.rectangle(roi, (x, y), (x+bw, y+bh), (0, 0, 255), 3)
                            break
                        elif left_area < right_area * 0.2:
                            out_msg.y = 1.0 # 强制右转
                            cv2.putText(roi, "CLOSE! TURN RIGHT", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 3)
                            cv2.rectangle(roi, (x, y), (x+bw, y+bh), (0, 0, 255), 3)
                            break

            # ====================================================
            # 3. 极简近场巡线 (没触发急转时执行)
            # ====================================================
            if not turn_triggered:
                # 只截取最底部的 40% 算中心，屏蔽中远景的干扰
                near_mask = mask[int(roi_h*0.6):roi_h, :]
                near_cx = self.get_center(near_mask, roi_w)
                
                if near_cx is not None:
                    out_msg.z = 1.0
                    out_msg.x = (near_cx - (roi_w / 2.0)) / (roi_w / 2.0)
                    cv2.circle(roi, (int(near_cx), int(roi_h*0.8)), 10, (0, 255, 0), -1)
                else:
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