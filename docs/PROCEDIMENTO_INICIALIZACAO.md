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

## Modo navegação com mapa salvo (AMCL)

Após ter um mapa salvo (ex: `maps/galpao_nav.yaml`), o modo de operação **estável** para navegação é usar AMCL em vez de SLAM ativo. Neste modo o mapa fica FIXO (não muda durante a operação), e o AMCL só localiza o robô dentro dele — bem mais robusto que SLAM ativo para navegação real.

### Terminal 1 — simulação + AMCL com mapa salvo

cd ~/robotica/robo-amr
ros2 launch rlai_bringup simulation.launch.py use_amcl:=true map_yaml_file:=/home/france/robotica/robo-amr/maps/galpao_nav.yaml

### Terminal 3 — Nav2

cd ~/robotica/robo-amr
ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true

Diferença para o modo SLAM ativo:
- O mapa não é atualizado durante a navegação — qualquer mudança no ambiente real não aparece no /map.
- O AMCL precisa de uma pose inicial razoável. Se a estimativa estiver muito errada, use o botão "2D Pose Estimate" no RViz/Foxglove para reposicionar.
- Recomendado para todas as sessões em que já existe mapa bom do ambiente. Use SLAM ativo apenas quando precisar mapear um ambiente novo.

Mapa de referência atual: `maps/galpao_nav.pgm` + `maps/galpao_nav.yaml` (399×399, 0.05 m/pix).

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

### Problema: bt_navigator em estado "unconfigured"

Causa: o lifecycle manager não conseguiu ativar o `bt_navigator` por timing/ordem de subida dos nós.

Verificação:
ros2 lifecycle get /bt_navigator

Deve responder `active`. Se responder `unconfigured` (ou outro estado), o BT não vai aceitar goals.

Solução: Ctrl+C no Terminal 3 (navigation) e subir novamente `ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true`. Geralmente na segunda tentativa fica `active`.

### Problema: DDS instável — `ros2 node info` não acha nós que existem

Causa: descoberta DDS ainda não estabilizou logo após subir os launches.

Solução: aguardar alguns segundos e repetir o comando. Se `ros2 node list` mostra o nó mas `ros2 node info <nome>` falha, é problema de descoberta, não de o nó estar morto.

### Problema: planner retorna "Start occupied" / inflation cobre todo o mapa

Causa: `inflation_radius` precisa ser no mínimo igual ao `circumscribed_radius` do robô (metade da maior dimensão do footprint). Para o AMR com garfos, o `circumscribed_radius` é **0.927 m** (medido pelo `planner_server` a partir do footprint `[[-0.28,-0.23],[-0.28,0.23],[0.86,0.23],[0.86,-0.23]]`). Se o `inflation_radius` for menor que esse valor, o Nav2 emite o aviso `The inflation radius (X) is smaller than the circumscribed radius (0.927200)` e o planejamento falha com "Start occupied", porque a célula onde o robô está aparece como ocupada no costmap inflado.

Tentativa malsucedida em 2026-05-25: reduzimos `inflation_radius` de 1.05 para 0.3 achando que o problema era inflation excessivo — mas 0.3 < 0.927 e causou exatamente a falha de planejamento descrita acima.

**Resolvido permanentemente** em 2026-05-26: `inflation_radius` definido como **`1.05`** no `src/rbot/navigation/rlai_navigation/config/nav2_params.yaml` (tanto no `global_costmap` quanto no `local_costmap`), valor confirmado em runtime. Backup do arquivo anterior em `nav2_params.yaml.bak.2026-05-26`.

### Problema: mapa do SLAM nasce bagunçado / com paredes duplicadas

Causa: o slam_toolbox 2D perde scan matching quando o robô se move rápido demais ou faz giros bruscos — o mesmo ambiente aparece em poses diferentes e duplica.

Solução: durante o mapeamento, dirigir **devagar**, com giros suaves e contínuos. Velocidades altas e mudanças bruscas de direção quebram a sequência de associações de scan. Se o mapa começou a ficar ruim, é melhor reiniciar o SLAM do zero do que tentar consertar dirigindo mais.

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
