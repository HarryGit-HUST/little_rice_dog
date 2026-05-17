#!/bin/bash

# ==============================================
# 🟢 【团队共用配置区 - 只需要改这里！】
# ==============================================
# 1. 仿真主工作空间路径 (固定不变)
SIM_WS="/home/cyberdog_sim"
# 2. 你的比赛代码工作空间路径 (可修改)
RACE_WS="/home/cyberdog_sim/src/my_race_code"
# 3. 视觉节点 (包名 + 节点名)
VISION_NODE="race_core vision_node"
# 4. 主控大脑节点 (包名 + 节点名)
MAIN_NODE="race_core main_brain"

# 会话名称 (一般不用改)
SESSION="cyberdog_race"

# ==============================================
# 🔴 【以下内容团队成员无需修改】
# ==============================================

# ======================
# 终端1: 启动 Gazebo 仿真（核心，必须最先启动）
# ======================
tmux new-session -d -s $SESSION
tmux send-keys -t $SESSION:0 "source /opt/ros/galactic/setup.bash && source /home/cyberdog_sim/install/setup.bash && source ${SIM_WS}/install/setup.bash && ros2 launch cyberdog_gazebo race_gazebo.launch.py" C-m

sleep 5
echo "✅ Gazebo 启动完成"

# ======================
# 终端2: 小脑控制（依赖Gazebo）
# ======================
tmux split-window -h -t $SESSION
tmux send-keys -t $SESSION:0.1 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && ros2 launch cyberdog_gazebo cyberdog_control_launch.py" C-m

sleep 3
echo "✅ 小脑控制节点启动完成"

# ======================
# 终端3: 视觉节点
# ======================
tmux split-window -v -t $SESSION
tmux send-keys -t $SESSION:0.2 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && source ${RACE_WS}/install/setup.bash && ros2 run ${VISION_NODE}" C-m

sleep 2
echo "✅ 视觉节点启动完成"

# ======================
# 终端4: 主控大脑（最后启动）
# ======================
tmux split-window -v -t $SESSION
tmux send-keys -t $SESSION:0.3 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && source ${RACE_WS}/install/setup.bash && ros2 run ${MAIN_NODE}" C-m

echo "✅ 所有节点启动完成！"
tmux attach-session -t $SESSION
