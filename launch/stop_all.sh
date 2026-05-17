#!/bin/bash
SESSION="cyberdog_race"

# 杀死所有ROS2进程
pkill -f ros2
pkill -f gazebo
pkill -f gzserver
pkill -f gzclient

# 关闭tmux会话
tmux kill-session -t $SESSION 2>/dev/null

echo "✅ 所有节点已停止，tmux会话已关闭"
