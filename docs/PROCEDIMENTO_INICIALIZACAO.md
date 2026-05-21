# Procedimento de inicialização — sistema Nav2 completo

Procedimento testado em 21/05/2026 que sobe simulação + SLAM + Nav2 funcionando.

## Pré-requisitos verificados (já configurados no ~/.bashrc)

- ROS 2 Jazzy sourceado
- GZ_SIM_RESOURCE_PATH inclui workspace local
- GZ_SIM_SYSTEM_PLUGIN_PATH configurado
- 9 pacotes rlai_* compilados em install/

## Sequência de inicialização

### Terminal 1 — simulação + SLAM

cd ~/robotica/robo-amr
ros2 launch rlai_bringup simulation.launch.py mapping_enabled:=true slam_rviz_enabled:=true

Espere 40 segundos. Gazebo e RViz vão abrir.

ATENÇÃO: Gazebo pode iniciar PAUSADO. Verifique no canto inferior esquerdo da janela do Gazebo:
- Se o botão for de PLAY (▶), simulação está pausada — clique para iniciar
- Se o botão for de PAUSE (II), simulação está rodando
- No canto inferior direito, "Sim time" deve estar crescendo continuamente

Se aparecer popup "ruby3.2 parou de funcionar inesperadamente": clique em "Não enviar". É crash de componente secundário do Gazebo que não afeta operação.

### Verificação — Terminal 2

Antes de subir navigation, verifique que TF está com timestamp correto:

cd ~/robotica/robo-amr
ros2 topic echo /tf --once

Procure o campo "sec" no header. Deve ser número alto (compatível com tempo simulado, ex: 50, 100, 200). Se for número baixo (ex: 2.018), reinicie o Terminal 1 — o SLAM iniciou antes do clock do Gazebo estabilizar.

Verifique também:

ros2 topic list | grep -E "tf|map|scan|odom"

Deve listar: /scan, /map, /tf, /tf_static, /odometry/filtered, /diff_drive_controller/odom.

### Terminal 3 — Nav2

Com TF verificada, suba Nav2:

cd ~/robotica/robo-amr
ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true

Espere 30 segundos.

### Validação final — Terminal 2

ros2 node list

Deve mostrar 32 nós, incluindo:
- /bt_navigator
- /planner_server
- /controller_server
- /global_costmap/global_costmap
- /local_costmap/local_costmap
- /behavior_server
- /slam_toolbox
- /ekf_node
- /velocity_smoother

Se faltar algum nó da Nav2, verifique o Terminal 3 — algum nó da stack pode ter falhado em ativar.

## Problemas conhecidos e soluções

### Problema: navigation falha com erro "Lookup would require extrapolation into the past"

Causa: SLAM publicou TF com timestamp dessincronizado do clock simulado, OU navigation subiu antes do SLAM estar pronto.

Solução:
1. Ctrl+C no Terminal 3 (navigation)
2. Ctrl+C no Terminal 1 (simulação)
3. ros2 node list no Terminal 2 — deve voltar vazio
4. Espere 5 segundos
5. Refazer sequência completa do procedimento

### Problema: Gazebo pausado

Causa: comportamento padrão do Gazebo Harmonic em algumas situações.

Solução: clicar no botão de play (▶) no canto inferior esquerdo da janela do Gazebo. Verificar que "Sim time" começa a crescer.

### Problema: arquivo .urdf.xacro não encontrado

Causa: build incremental do colcon perdeu algum arquivo.

Solução:
cd ~/robotica/robo-amr
colcon build --packages-select rlai_description
[abrir terminal novo para refletir o source]

## Layout recomendado de terminais

| Terminal | Função | Permanência |
|---|---|---|
| 1 | ros2 launch simulation.launch.py | Mantém aberto durante toda a sessão |
| 2 | Inspeção (ros2 node list, topic echo, etc) | Reaproveita para vários comandos |
| 3 | ros2 launch navigation.launch.py | Mantém aberto durante toda a sessão |

Para teleop (dirigir o robô manualmente), abrir Terminal 4 separado.

## Tempo total esperado

- Subir simulação: 40s
- Verificar TF: 5s
- Subir navigation: 30s
- Total: ~75 segundos do zero até sistema pronto
