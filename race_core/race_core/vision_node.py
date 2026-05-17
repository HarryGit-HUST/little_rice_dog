#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import cv2
import numpy as np
from rclpy.qos import qos_profile_sensor_data

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        # 订阅相机图像 (注意：必须使用 sensor_data QoS，否则接不到 Gazebo 图像流)
        self.sub_image = self.create_subscription(
            Image, '/cyberdog_camera/image_raw', self.image_callback, qos_profile_sensor_data)
        
        # 发布计算好的偏差
        self.pub_error = self.create_publisher(Float32, '/perception/line_error', 10)
        self.bridge = CvBridge()
        self.get_logger().info("👁️ 视觉节点已启动，盯紧黄线中...")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            h, w, _ = cv_image.shape
            
            # 1. 裁剪感兴趣区域 (ROI)：只看画面下半部分，避免被远处的黄色背景干扰
            roi = cv_image[int(h/2):h, :]
            
            # 2. 颜色提取：转到 HSV 空间找赛道黄
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([20, 100, 100])
            upper_yellow = np.array([40, 255, 255])
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            
            # 为了平滑，稍微做个形态学滤波
            mask = cv2.erode(mask, None, iterations=2)
            mask = cv2.dilate(mask, None, iterations=2)

            # 3. 寻找黄线的质心
            M = cv2.moments(mask)
            if M['m00'] > 0:
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                
                # 计算偏差：目标中心减去画面中心
                # 正数表示线在右边，负数表示线在左边
                error = float(cx - (w / 2))
                self.pub_error.publish(Float32(data=error))
                
                # [调试用] 绘制中心点
                cv2.circle(roi, (cx, cy), 10, (255, 0, 0), -1)
            else:
                # 画面里没看到黄线，发个极值 999 告诉大脑盲走
                self.pub_error.publish(Float32(data=999.0))
            
            # [调试用] 弹窗显示，确定你的 HSV 参数是对的
            cv2.imshow("Dog Vision ROI", roi)
            cv2.waitKey(1)
            
        except Exception as e:
            self.get_logger().error(f"图像处理崩了: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()