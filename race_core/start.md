
#### 第 2 步：终极四开测试流（完全指南）

为了绝不串线，我们需要开 4 个独立的 Docker 终端（`sudo docker exec -it cyberdog_dev /bin/bash`）。请严格按照以下指令复制执行：

**【终端 1：创造世界 (只 source 官方)】**
```bash
cd /home/cyberdog_sim
source /opt/ros/galactic/setup.bash
source install/setup.bash
ros2 launch cyberdog_gazebo race_gazebo.launch.py
```
*(等待 Gazebo 弹出来)*

**【终端 2：激活小脑 (只 source 官方)】**
```bash
cd /home/cyberdog_sim
source /opt/ros/galactic/setup.bash
source install/setup.bash
ros2 launch cyberdog_gazebo cyberdog_control_launch.py
```
*(必须跑这个，否则时间是静止的，相机不会出图，狗也不会动！)*

**【终端 3：视觉感知组 (双重 source)】**
```bash
# 1. 先引入全局 ROS2 环境
source /opt/ros/galactic/setup.bash

# 2. 再引入官方小车环境
source /home/cyberdog_sim/install/setup.bash

# 3. 最后引入你的代码包环境
source /home/cyberdog_sim/src/my_race_code/install/setup.bash
ros2 run race_core vision_node
```
*(这次改完 QoS，绿十字瞄准镜一定会出现！)*

**【终端 4：主控架构组 (双重 source)】**
```bash
cd /home/cyberdog_sim
source install/setup.bash
cd src/my_race_code
source install/setup.bash
source /opt/ros/galactic/setup.bash

# 2. 再引入官方小车环境
source /home/cyberdog_sim/install/setup.bash

# 3. 最后引入你的代码包环境
source /home/cyberdog_sim/src/my_race_code/install/setup.bash
ros2 run race_core main_brain
```

### 接下来见证魔法的时刻：
只要这四个终端按照顺序跑起来，你会看到：
1. `vision_node` 弹出一个窗口，你能看到赛道的画面。
2. `main_brain` 的输出会从 `0.00` 变成真正的偏差值（比如 `Error: 15.3, Angular: -0.07`）。
3. Gazebo 里的机器狗，会开始缓慢地根据误差调整自己的姿态！

去执行吧！只要出图了，你们团队的第一关架构就彻底立住了！截图发给我！