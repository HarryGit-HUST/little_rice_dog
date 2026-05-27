#!/bin/bash

# ==============================================
# 🟢 【团队共用配置区 - 只需要改这里！】
# ==============================================
# 1. 仿真主工作空间路径 (固定不变)
SIM_WS="/home/cyberdog_sim"
# 2. 你的比赛代码工作空间路径 (可修改)
RACE_WS="/home/cyberdog_sim/src/my_race_code"
# 3. 队友的底层工具箱路径 (固定不变)
UTILS_DIR="/home/cyberdog_utils"
# 4. 视觉节点 (包名 + 节点名)
VISION_NODE="race_core yellow_line_detector"
# 5. 主控大脑节点 (包名 + 节点名)
MAIN_NODE="race_core main_brain"

# 会话名称 (一般不用改)
SESSION="cyberdog_race"

# ==============================================
# 🔴 【以下内容团队成员无需修改】
# ==============================================

# 确保清除历史僵尸进程
killall -9 gzserver gzclient > /dev/null 2>&1

# ======================
# 终端1: 启动 Gazebo 仿真（核心，必须最先启动）
# ======================
tmux new-session -d -s $SESSION
tmux send-keys -t $SESSION:0 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && ros2 launch cyberdog_gazebo race_gazebo.launch.py paused:=false" C-m

sleep 8
echo "✅ 1/5 Gazebo 物理世界启动完成 (已自动解除暂停)"

# ======================
# 终端2: 小脑控制（依赖Gazebo）
# ======================
tmux split-window -h -t $SESSION
tmux send-keys -t $SESSION:0.1 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && ros2 launch cyberdog_gazebo cyberdog_control_launch.py" C-m

sleep 5
echo "✅ 2/5 小脑控制节点启动完成"

# ======================
# 终端3: 🌟【新增】底盘位姿广播器 (提供 /pose 话题，由队友编写)
# ======================
tmux split-window -v -t $SESSION -p 75
tmux send-keys -t $SESSION:0.2 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && python3 ${RACE_WS}/race_core/race_core/pose_broadcaster.py" C-m

sleep 2
echo "✅ 3/5 底盘位姿广播器启动完成 (已提供 /pose)"

# ======================
# 终端4: 视觉节点 (黄线及急弯识别)
# ======================
tmux split-window -v -t $SESSION -p 66
tmux send-keys -t $SESSION:0.3 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && source ${RACE_WS}/install/setup.bash && ros2 run ${VISION_NODE}" C-m

sleep 2
echo "✅ 4/5 视觉节点启动完成"

# ======================
# 终端5: 主控大脑（最后启动，接管全局）
# ======================
# 确保 cyberdog_control 已经在运行，否则主控大脑的心跳包无人接收
echo "⏳ 等待 cyberdog_control 就绪..."
for i in $(seq 1 30); do
    if ps aux | grep -v grep | grep -q "cyberdog_control"; then
        echo "✅ cyberdog_control 已就绪 (耗时 ${i}s)"
        break
    fi
    sleep 1
done
if ! ps aux | grep -v grep | grep -q "cyberdog_control"; then
    echo "❌ cyberdog_control 启动失败！请检查控制终端"
    exit 1
fi
tmux split-window -v -t $SESSION -p 50
tmux send-keys -t $SESSION:0.4 "source /opt/ros/galactic/setup.bash && source ${SIM_WS}/install/setup.bash && source ${RACE_WS}/install/setup.bash && ros2 run ${MAIN_NODE}" C-m

echo "✅ 5/5 所有节点启动完成！控制台已合并！"
tmux attach-session -t $SESSION