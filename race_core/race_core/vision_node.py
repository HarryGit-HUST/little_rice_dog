#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
from rclpy.qos import qos_profile_sensor_data
import cv2
import numpy as np

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        # 订阅狗的眼睛
        # 订阅狗的眼睛 (务必使用 sensor_data QoS，否则接不到 Gazebo 的视频流！)
        self.sub_image = self.create_subscription(
            Image, 
            '/cyberdog_camera/image_raw', 
            self.image_callback, 
            qos_profile_sensor_data)
        # 发布给大脑的“偏差”数据
        self.pub_error = self.create_publisher(Float32, '/perception/line_error', 10)
        
        self.bridge = CvBridge()
        self.get_logger().info("视觉感知节点 [Vision Node] 启动，正在寻找黄线...")

    def image_callback(self, msg):
        try:
            # 1. 转化为 OpenCV 图像
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            height, width, _ = cv_image.shape

            # 2. 截取图像下半部分 (ROI) 以消除远处干扰
            roi = cv_image[int(height/2):height, 0:width]
            
            # 3. 提取黄色 (赛道黄线的 HSV 范围，需根据实际光照微调)
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

            # 4. 寻找最大轮廓的质心 (重力中心)
            M = cv2.moments(mask)
            if M['m00'] > 0:
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                
                # 计算偏差：目标中心 - 屏幕中心
                # error > 0: 线在右边，狗需要右转; error < 0: 线在左边，狗需要左转
                error = float(cx - (width / 2))
                
                # 发布给大脑
                error_msg = Float32()
                error_msg.data = error
                self.pub_error.publish(error_msg)

                # --- 调试可视化 (仅在电脑端测试用) ---
                cv2.circle(roi, (cx, cy), 10, (0, 0, 255), -1)
                cv2.imshow("Yellow Line Tracker", roi)
                cv2.waitKey(1)
            else:
                # 没找到黄线
                self.pub_error.publish(Float32(data=999.0)) # 999 作为一个特殊标记符

        except Exception as e:
            self.get_logger().error(f"视觉处理异常: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()