#!/bin/bash
# Script para subir a stack completa Nav2 com simulação e SLAM
# Procedimento documentado em docs/PROCEDIMENTO_INICIALIZACAO.md
# Versão anterior salva em start_nav2_stack.sh.backup_20260525

set -e

WORKSPACE="$HOME/robotica/robo-amr"
cd "$WORKSPACE"

echo "================================================================"
echo "  Stack Nav2 — inicialização automatizada"
echo "================================================================"
echo ""
echo ">>> ATENÇÃO: se o Gazebo abrir PAUSADO (botão de play ▶ visível"
echo "    no canto inferior esquerdo), clique no play para iniciar a"
echo "    simulação. Sem isso o clock simulado não avança e o SLAM/Nav2"
echo "    não conseguem rodar."
echo ""

echo "Iniciando simulação + SLAM no Terminal 1..."
gnome-terminal --tab --title="SIM+SLAM" -- bash -c "cd $WORKSPACE && ros2 launch rlai_bringup simulation.launch.py mapping_enabled:=true slam_rviz_enabled:=true; exec bash"

# Espera maior para dar tempo da descoberta DDS estabilizar
echo "Aguardando 50 segundos para simulação + SLAM inicializarem e DDS estabilizar..."
sleep 50

echo "Verificando TF..."
TF_OUTPUT=$(timeout 5 ros2 topic echo /tf --once 2>&1 || echo "ERRO_TF")
if echo "$TF_OUTPUT" | grep -q "ERRO_TF"; then
    echo "AVISO: não consegui verificar TF. Possíveis causas:"
    echo "  - Gazebo ainda está pausado (clique play)"
    echo "  - Descoberta DDS instável — aguarde mais alguns segundos e repita"
    echo "  - SLAM falhou em subir — veja Terminal 1"
    echo "Veja docs/PROCEDIMENTO_INICIALIZACAO.md"
    exit 1
fi

echo "TF detectada. Iniciando Nav2 no Terminal 3..."
gnome-terminal --tab --title="NAV2" -- bash -c "cd $WORKSPACE && ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true; exec bash"

echo "Aguardando 30 segundos para Nav2 ativar todos os nós..."
sleep 30

# Verificação de lifecycle do bt_navigator
echo ""
echo "Verificando estado do bt_navigator..."
BT_STATE=$(timeout 5 ros2 lifecycle get /bt_navigator 2>&1 || echo "FALHA")
echo "  bt_navigator: $BT_STATE"
if ! echo "$BT_STATE" | grep -q "active"; then
    echo ""
    echo "  >>> AVISO: bt_navigator NÃO está 'active'."
    echo "  >>> Solução: Ctrl+C no Terminal 3 (NAV2) e suba novamente:"
    echo "      ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true"
    echo "  >>> Veja seção 'Problemas conhecidos' em docs/PROCEDIMENTO_INICIALIZACAO.md"
else
    echo "  OK — bt_navigator pronto para receber goals."
fi

echo ""
echo "================================================================"
echo "Stack completa subindo."
echo "Para verificar nós ativos:"
echo "  ros2 node list"
echo ""
echo "Se algum comando 'ros2 node info' não achar nó que existe,"
echo "repita após alguns segundos — descoberta DDS demora a estabilizar."
echo "================================================================"
