#!/bin/bash
# Script para subir a stack completa Nav2 com simulação e SLAM
# Procedimento documentado em docs/PROCEDIMENTO_INICIALIZACAO.md

set -e

WORKSPACE="$HOME/robotica/robo-amr"
cd "$WORKSPACE"

echo "Iniciando simulação + SLAM no Terminal 1..."
gnome-terminal --tab --title="SIM+SLAM" -- bash -c "cd $WORKSPACE && ros2 launch rlai_bringup simulation.launch.py mapping_enabled:=true slam_rviz_enabled:=true; exec bash"

echo "Aguardando 40 segundos para simulação inicializar..."
sleep 40

echo "Verificando TF..."
TF_OUTPUT=$(timeout 5 ros2 topic echo /tf --once 2>&1 || echo "ERRO_TF")
if echo "$TF_OUTPUT" | grep -q "ERRO_TF"; then
    echo "AVISO: não consegui verificar TF. Tente subir navigation manualmente."
    echo "Veja docs/PROCEDIMENTO_INICIALIZACAO.md"
    exit 1
fi

echo "TF detectada. Iniciando Nav2 no Terminal 3..."
gnome-terminal --tab --title="NAV2" -- bash -c "cd $WORKSPACE && ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true; exec bash"

echo ""
echo "Stack completa subindo. Aguarde mais 30 segundos."
echo "Para verificar nós ativos:"
echo "  ros2 node list"
echo ""
echo "ATENÇÃO: se Gazebo iniciar pausado, clique no botão play (▶) no canto inferior esquerdo da janela."
