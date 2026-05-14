# Guia de Navegação do Código `src/rbot/`

> **Para quem é este documento.** Você é engenheiro mecânico começando a estudar
> a stack ROS 2 do rbot adotado como base do projeto. Este guia mostra **onde
> mora cada coisa**, **em que camada ela vive**, e **o que mudar quando você
> quiser alterar uma característica do robô** — sem precisar ler o código todo
> antes de tocar em nada.
>
> Última atualização: 2026-05-14 · Caminhos a partir de `/workspace/src/rbot/`.

---

## 1. Arquitetura em camadas

Pense no robô como uma pilha (igual a desenho de "system stack" em
engenharia mecatrônica). De baixo (físico) para cima (decisão):

```
┌──────────────────────────────────────────────────────────────────────────┐
│  5. MISSÃO / APLICAÇÃO                                                   │
│     "Pegue o pallet X e leve para a doca Y."                             │
│     Quem decide o quê fazer. Hoje no rbot é só goal manual.              │
│     >>> NOSSA CAMADA (vai virar src/rbot/missions/rlai_logistics/)       │
├──────────────────────────────────────────────────────────────────────────┤
│  4. NAVEGAÇÃO (Nav2)                                                     │
│     Planejador global + controlador local + behavior tree.               │
│     Recebe goal (x,y,θ), produz /cmd_vel.                                │
│     navigation/rlai_navigation/                                          │
│                                                                          │
│     ┌─ planner_server ── SMAC Hybrid-A* ─┐                               │
│     │  controller_server ─ MPPI ─────────┤  costmaps                     │
│     │  bt_navigator ─── behavior tree ───┤  (global+local)               │
│     │  behavior_server ─ spin/backup ────┘                               │
│     └─ smoother_server ─ SimpleSmoother                                  │
├──────────────────────────────────────────────────────────────────────────┤
│  3.5 LOCALIZAÇÃO                                                         │
│     EKF (odom→base_footprint) + AMCL (map→odom) + IMU Madgwick filter.   │
│     localization/rlai_localization/                                      │
│     Sem isso, Nav2 não sabe onde o robô está.                            │
├──────────────────────────────────────────────────────────────────────────┤
│  3. ros2_control (controle de baixo nível)                               │
│     Recebe /cmd_vel e converte em torque por roda (cinemática inversa    │
│     diff-drive). Publica odometria pelas rodas.                          │
│     control/rlai_control/config/controllers.yaml                         │
│                                                                          │
│     diff_drive_controller     ←  velocity_smoother  ←  Nav2 /cmd_vel     │
│     joint_state_broadcaster   →  /joint_states                           │
├──────────────────────────────────────────────────────────────────────────┤
│  2. DRIVERS / PLUGINS DO GAZEBO                                          │
│     "Quem move os joints" e "quem gera dados de sensor".                 │
│     robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro         │
│                                                                          │
│     gz_ros2_control-system  →  faz os joints obedecerem aos controllers  │
│     gpu_lidar               →  produz /scan a 15 Hz                      │
│     imu, depth_camera, ...  →  cada sensor tem seu plugin                │
│                                                                          │
│     (No robô real: substituídos por drivers do fabricante — RPLIDAR,     │
│     Intel RealSense, IMU Bosch, etc. — mesmos tópicos ROS.)              │
├──────────────────────────────────────────────────────────────────────────┤
│  1. URDF — DESCRIÇÃO FÍSICA                                              │
│     "O CAD do robô para o software." Massa, inércia, dimensões,          │
│     posição dos joints, posição dos sensores.                            │
│     robot/rlai_description/urdf/                                         │
│                                                                          │
│     robot.urdf.xacro              ← arquivo raiz (monta o robô)          │
│     ├─ base/base.urdf.xacro       ← chassi                               │
│     ├─ base/wheels.urdf.xacro     ← rodas tração + casters               │
│     ├─ sensors/lidar_2d.urdf.xacro ... ← uma macro por sensor            │
│     └─ control/ros2_control.urdf.xacro ← interface joints→controllers    │
└──────────────────────────────────────────────────────────────────────────┘
```

**Analogia mecânica.** A camada 1 (URDF) é o "modelo de CAD com massa e
inércia". A camada 2 (Gazebo) é o "ambiente de simulação tipo Adams/Simulink"
que aplica forças. A camada 3 (ros2_control) é o "controlador PID embarcado"
que decide quanta corrente vai para cada motor. As camadas 3.5 a 5 são
software puro: estimadores de estado, planejadores, lógica de missão.

**Regra prática.** Quando mudar a camada N, sempre verifique se a camada
N+1 (acima) ainda assume números compatíveis. Exemplo: trocar raio da roda
(camada 1) sem atualizar `controllers.yaml` (camada 3) faz a odometria
mentir e o robô anda errado.

---

## 2. Onde muda o quê

Os números de linha são aproximados (HEAD `b8095e7`); use grep se mudar.

### 2.1 Geometria e massa do robô (URDF)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Separação entre rodas tração** (wheel_separation) | `robot/rlai_description/urdf/robot.urdf.xacro` | 45 | Editar arg da macro `<xacro:rlai_wheels …/>` |
| **Raio da roda tração** | `robot/rlai_description/urdf/robot.urdf.xacro` | 45 | Idem (`wheel_radius="0.0625"`) |
| **Largura da roda tração** | `robot/rlai_description/urdf/base/wheels.urdf.xacro` | 41 | `<cylinder length="0.040"/>` (collision) e mesh visual |
| **Massa da roda** | `robot/rlai_description/urdf/base/wheels.urdf.xacro` | 45 | `<mass value="1.5"/>` |
| **Quantidade de rodas tração** | `robot/rlai_description/urdf/base/wheels.urdf.xacro` | 68–75 + 11–66 | Hoje 2 (left/right). Mudar exige reescrever a macro `rlai_wheels` e portar para `diff_drive_controller` → ackermann/skid_steer_controller. **Não é uma linha**. |
| **Quantidade/posição dos casters** | `robot/rlai_description/urdf/base/wheels.urdf.xacro` | 77+ | Bloco de 4 casters; cada um tem `<origin xyz="${x} ${y} 0"/>` |
| **Dimensões do chassi** (comprimento × largura × altura) | `robot/rlai_description/urdf/base/base.urdf.xacro` | 58 | `<box size="0.50 0.40 0.15"/>` (collision) + visuals |
| **Massa do chassi** | `robot/rlai_description/urdf/base/base.urdf.xacro` | 63 | `<mass value="15.0"/>` |
| **Tensor de inércia do chassi** | `robot/rlai_description/urdf/base/base.urdf.xacro` | 71–73 | `ixx ixy ixz iyy iyz izz` — recalcular se mudar massa/dimensão |

### 2.2 Sensores (posição, taxa, ruído)

A posição de cada sensor vem da chamada da macro em `robot.urdf.xacro`
(`xyz=…`). A taxa e o ruído vem do plugin Gazebo correspondente.

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Posição do LiDAR 2D** | `robot/rlai_description/urdf/robot.urdf.xacro` | 54 | `xyz="0.20 0.0 0.18"` na chamada `<xacro:rlai_lidar_2d …/>` |
| **Posição da IMU** | `robot/rlai_description/urdf/robot.urdf.xacro` | 48 | `xyz="0.0 0.0 0.08"` |
| **Posição da câmera RGB-D** | `robot/rlai_description/urdf/robot.urdf.xacro` | 69 | `xyz="0.237 0.0 0.125"` |
| **Habilitar / desabilitar sensor** | `bringup/rlai_bringup/launch/simulation.launch.py` | 70–75 | Args `lidar_3d_enabled`, `gps_enabled`, etc. (passar `lidar_3d_enabled:=true` na CLI) |
| **Modelo de LiDAR** (RPLIDAR vs Hokuyo) | `robot/rlai_description/urdf/robot.urdf.xacro` | 18 | Arg `lidar_2d_model` (default `rplidar_a3`) |
| **Taxa de amostragem LiDAR 2D** (`update_rate` Hz) | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 43 | `<update_rate>15</update_rate>` |
| **Resolução angular do LiDAR 2D** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 49 | `<samples>720</samples>` (= 0.5° por raio) |
| **Alcance min/máx do LiDAR 2D** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 56–58 | `<min>0.30</min><max>25.0</max>` |
| **Ruído gaussiano do LiDAR** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 60–64 | `<stddev>0.01</stddev>` |
| **Taxa da IMU** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 120 | `<update_rate>200</update_rate>` |
| **Taxa da câmera RGB-D** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 161 / 184 | `<update_rate>30</update_rate>` (depth e RGB separados) |
| **FOV da câmera** | `robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` | 165 / 188 | `<horizontal_fov>1.5184</horizontal_fov>` (radianos; 87°) |
| **Adicionar sensor novo** | `robot/rlai_description/urdf/sensors/<novo>.urdf.xacro` (criar) | — | (1) escrever macro do link/joint, (2) incluir em `robot.urdf.xacro`, (3) plugin Gazebo em `gazebo_sensors.urdf.xacro`, (4) ruído em `config/sensor_noise.yaml`, (5) arg em `simulation.launch.py`. |
| **Remover sensor** | — | — | Setar arg `=false` no launch (não precisa editar URDF) |

### 2.3 Limites cinemáticos e controle (ros2_control)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Velocidade linear máxima** (m/s) | `control/rlai_control/config/controllers.yaml` | 45 | `max_velocity: 0.5` (linear.x). **Também mexer em `nav2_params.yaml:48` (`vx_max` MPPI) e `velocity_smoother.yaml:16`** |
| **Velocidade de ré** | `control/rlai_control/config/controllers.yaml` | 46 | `min_velocity: -0.35` |
| **Velocidade angular máxima** (rad/s) | `control/rlai_control/config/controllers.yaml` | 55 | `max_velocity: 1.9`. **Espelhar em `nav2_params.yaml:51` (`wz_max`)** |
| **Aceleração linear** (m/s²) | `control/rlai_control/config/controllers.yaml` | 48 | `max_acceleration: 1.0`. **Espelhar em `velocity_smoother.yaml:19`** |
| **Aceleração angular** (rad/s²) | `control/rlai_control/config/controllers.yaml` | 58 | `max_acceleration: 3.2` |
| **Frequência do `controller_manager`** | `control/rlai_control/config/controllers.yaml` | 6 | `update_rate: 100` Hz (loop do ros2_control que escreve nos joints) |
| **Frequência de publicação da odometria** | `control/rlai_control/config/controllers.yaml` | 38 | `odom_publish_rate: 50` |
| **Wheel_separation usada na odometria** | `control/rlai_control/config/controllers.yaml` | 25 | **DEVE bater com URDF linha 45** |
| **Wheel_radius usado na odometria** | `control/rlai_control/config/controllers.yaml` | 26 | **DEVE bater com URDF linha 45** |
| **Covariância de pose/twist da odom** | `control/rlai_control/config/controllers.yaml` | 40–41 | Lida pelo EKF. Diminuir = "confio mais nas rodas" |
| **Torque do motor** | `robot/rlai_description/urdf/control/ros2_control.urdf.xacro` | (procurar `<command_interface name="effort">` ou `<limit effort=…>` no URDF joint) | Para diff-drive padrão o controle é por **velocidade**, não torque. Se quiser controle por torque, trocar `<command_interface name="velocity">` por `effort` e migrar para `effort_controllers/JointGroupEffortController`. **Mudança grande.** |

### 2.4 Localização (EKF, AMCL, IMU filter)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Frequência do EKF** | `localization/rlai_localization/config/ekf.yaml` | — | Não declarada → default `30` Hz. Adicionar `frequency: 50` se quiser mais rápido |
| **Quais sensores o EKF funde** | `localization/rlai_localization/config/ekf.yaml` | 42–66 | `odom0_config` e `imu0_config` são matrizes 15×1 (x,y,z, roll,pitch,yaw, vx,vy,vz, vroll,vpitch,vyaw, ax,ay,az) — `true` = funde aquele estado |
| **Nº de partículas do AMCL** | `localization/rlai_localization/config/amcl.yaml` | 43–44 | `min_particles: 500`, `max_particles: 2000` |
| **Disparo de update do AMCL** | `localization/rlai_localization/config/amcl.yaml` | 59–60 | `update_min_d: 0.2` m, `update_min_a: 0.2` rad |
| **Ruído de motion model AMCL** | `localization/rlai_localization/config/amcl.yaml` | 25–28 | `alpha1..4` |
| **Pose inicial do AMCL** | `localization/rlai_localization/config/amcl.yaml` | 74–75 | `set_initial_pose: true` + bloco `initial_pose` |
| **Ganho do filtro Madgwick (IMU)** | `localization/rlai_localization/config/imu_filter.yaml` | 34 | `gain: 0.1` (β) — maior = mais correção gyro, menos suavização |

### 2.5 Navegação (Nav2)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Footprint do robô** (polígono colisão) | `navigation/rlai_navigation/config/nav2_params.yaml` | 218 (global) + 274 (local) | `footprint: "[[-0.28,-0.23],...]"`. **Sempre nos dois locais.** |
| **Padding do footprint** | `nav2_params.yaml` | 219 / 275 | `footprint_padding: 0.03` |
| **Raio de inflação** (custom decay) | `nav2_params.yaml` | 245 / 296 | `inflation_radius: 0.55` |
| **Frequência do controller (MPPI)** | `nav2_params.yaml` | 11 | `controller_frequency: 20.0` Hz |
| **Velocidade máx que o MPPI usa** | `nav2_params.yaml` | 48–51 | `vx_max: 0.5`, `wz_max: 1.9` (espelham `controllers.yaml`) |
| **Horizonte do MPPI** | `nav2_params.yaml` | 42–44 | `time_steps: 56`, `model_dt: 0.05` (56 × 50 ms = 2.8 s) |
| **Nº de trajetórias amostradas MPPI** | `nav2_params.yaml` | 44 | `batch_size: 2000` — maior = melhor, mais CPU |
| **Pesos dos críticos MPPI** | `nav2_params.yaml` | 70+ | `CostCritic.cost_weight`, `GoalCritic.cost_weight`, … |
| **Raio mínimo de curva (SMAC)** | `nav2_params.yaml` | 152 | `minimum_turning_radius: 0.25` m — 0.0 = giro no lugar |
| **Resolução angular SMAC** | `nav2_params.yaml` | 142 | `angle_quantization_bins: 72` (5° por bin) |
| **Tempo máximo de planejamento** | `nav2_params.yaml` | 163 | `max_planning_time: 5.0` s |
| **Tolerância do goal (planner)** | `nav2_params.yaml` | 147 | `tolerance: 0.5` m |
| **Update rate do global_costmap** | `nav2_params.yaml` | 213–214 | `update_frequency: 1.0`, `publish_frequency: 1.0` |
| **Update rate do local_costmap** | `nav2_params.yaml` | 262–263 | `update_frequency: 5.0`, `publish_frequency: 2.0` |
| **Janela do local_costmap** | `nav2_params.yaml` | 270–271 | `width: 3`, `height: 3` (m) |
| **Tópico do laser usado pelos costmaps** | `nav2_params.yaml` | 236 / 286 | `topic: /scan` |
| **Velocidade do spin (recovery)** | `nav2_params.yaml` | 364–366 | `max_rotational_vel: 1.0`, `rotational_acc_lim: 3.2` |
| **Behavior tree XML** | `navigation/rlai_navigation/behavior_trees/navigate_to_pose.xml` | — | Edita o BT diretamente (XML do BehaviorTree.CPP) |

### 2.6 Velocity smoother (entre Nav2 e o controller)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Frequência do smoother** | `control/rlai_control/config/velocity_smoother.yaml` | 8 | `smoothing_frequency: 20.0` Hz |
| **Velocidade máx/mín** | `velocity_smoother.yaml` | 16–17 | `max_velocity: [0.5, 0.0, 1.9]` |
| **Aceleração / desaceleração** | `velocity_smoother.yaml` | 19–20 | `max_accel: [1.0, 0.0, 3.2]` / `max_decel: [-1.0, 0.0, -3.2]` |
| **Timeout de zero velocity** | `velocity_smoother.yaml` | 26 | `velocity_timeout: 1.0` s |

### 2.7 Mapping (SLAM Toolbox)

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Resolução do mapa SLAM** | `mapping/rlai_mapping/config/slam_toolbox_online_async.yaml` | 59 | `resolution: 0.05` m/célula |
| **Frequência de publicação do mapa** | `slam_toolbox_online_async.yaml` | 60 | `map_update_interval: 5.0` s |
| **Distância para acionar update** | `slam_toolbox_online_async.yaml` | 67–68 | `minimum_travel_distance: 0.3`, `minimum_travel_heading: 0.3` |
| **Distância máx para loop closure** | `slam_toolbox_online_async.yaml` | 74 | `loop_search_maximum_distance: 2.0` |

### 2.8 Simulação / mundo Gazebo

| Quero mudar… | Arquivo | Linha aprox | Tipo de mudança |
|---|---|---|---|
| **Mundo padrão** | `bringup/rlai_bringup/launch/simulation.launch.py` | 59 | `world` arg (default `small_warehouse`). Mundos disponíveis: `empty`, `small_warehouse`, `large_warehouse`, `office_floor`, `outdoor_courtyard` |
| **Pose inicial do robô** | `simulation.launch.py` | 60–63 | `x:=1.0 y:=1.0 yaw:=0.0` na CLI |
| **Headless vs GUI** | `simulation.launch.py` | 64–68 | `headless:=true` para sem GUI |
| **Adicionar um novo mundo .sdf** | `simulation/rlai_gazebo/worlds/<novo>.sdf` (criar) | — | Copiar `small_warehouse.sdf` como template, mudar nome, declarar como mundo válido em `simulation.launch.py:59 choices` se quiser validação |
| **Adicionar modelo (pallet, doca, …)** | `simulation/rlai_gazebo/models/<modelo>/` (criar) | — | Cada modelo é um diretório com `model.sdf` + `model.config` + meshes. Instanciar no `.sdf` do mundo com `<include><uri>model://nome</uri></include>` |
| **Mapa 2D (AMCL)** | `simulation.launch.py` | 91–95 | Arg `map_yaml_file`. Mapas hoje: `/workspace/rbot/maps/{my_map,small_warehouse,empty_world}.yaml` — quando portarmos o galpão, geramos um novo via SLAM e salvamos aqui |

---

## 3. Fluxo de uma mudança típica

**Exemplo: aumentar o raio da roda de 6.25 cm para 8 cm.**

1. **URDF.** `robot.urdf.xacro:45` → `wheel_radius="0.080"`.
2. **Recalcular inércia da roda.** Cilindro: I = ½ m r². `wheels.urdf.xacro` → atualizar bloco `<inertia>` (não tão crítico para sim, é crítico para hardware).
3. **Mesh visual.** Se o STL tinha 12.5 cm de diâmetro, ou troca o STL (`robot/rlai_meshes/meshes/wheel.stl`) ou aceita que visualmente está errado mas a collision (cylinder) está certa.
4. **ros2_control.** `controllers.yaml:26` → `wheel_radius: 0.080`. **Senão a odometria mente** (sub/superestima distância percorrida).
5. **Re-build.** `colcon build --packages-select rlai_description rlai_control`.
6. **Re-run** e validar que `/diff_drive_controller/odom` integra distância correta dirigindo 1 m em linha reta.

**Padrão geral.** "Mudei número físico → procurar todos os lugares que copiam esse número". Pares clássicos que precisam ficar sincronizados:

| Par sincronizado | Onde | Consequência se divergir |
|---|---|---|
| `wheel_separation` URDF ↔ `controllers.yaml` | `robot.urdf.xacro:45` + `controllers.yaml:25` | Odometria angular errada (giros mentem) |
| `wheel_radius` URDF ↔ `controllers.yaml` | `robot.urdf.xacro:45` + `controllers.yaml:26` | Odometria linear errada |
| `max_velocity` controllers ↔ MPPI ↔ smoother | `controllers.yaml:45` + `nav2_params.yaml:48` + `velocity_smoother.yaml:16` | Nav2 manda velocidade > limite físico → smoother corta → Nav2 acha que falhou |
| Footprint global ↔ local costmap | `nav2_params.yaml:218` + `:274` | Robô passa "raspando" em um mas não no outro |
| `laser_max_range` AMCL ↔ obstacle_layer | `amcl.yaml:33` + `nav2_params.yaml:235`/`285` | Inconsistência entre o que o AMCL "vê" para localização vs. o que o costmap usa |

---

## 4. Comandos úteis para explorar o código

```bash
# Buscar onde um parâmetro é usado
cd /workspace/src/rbot
grep -rn "wheel_radius" .

# Visualizar URDF montado (depois do build)
source /workspace/install/setup.bash
ros2 launch rlai_description display.launch.py   # abre RViz com URDF

# Rebuild só o pacote que você editou
cd /workspace && colcon build --packages-select <pkg> --symlink-install

# Listar tópicos publicados em runtime
ros2 topic list
ros2 topic echo --once /scan | head -20
ros2 topic hz /diff_drive_controller/odom

# Ver árvore de TFs
ros2 run tf2_tools view_frames

# Ver estado lifecycle dos nodos Nav2
ros2 lifecycle get /controller_server
```

---

## 5. Glossário rápido (para mecânicos)

| Termo ROS | Tradução mecânica |
|---|---|
| **URDF / xacro** | "CAD com massa, inércia e joints" — versão XML usada pelo ROS. xacro = URDF + macros e variáveis. |
| **Joint** | Vínculo cinemático. `continuous` = revoluta sem limite (roda). `prismatic` = linear (garfo). `fixed` = solda. |
| **Link** | Corpo rígido. Tem massa, inércia, geometria visual e de colisão. |
| **TF** | Árvore de transformações entre frames (igual sistemas de coordenadas em CAD). |
| **Topic** | Canal pub/sub (igual sinal num diagrama de blocos Simulink). |
| **Service / Action** | Chamada síncrona (service) ou de longa duração com feedback (action — usado por Nav2). |
| **Lifecycle node** | Nodo com estados: unconfigured → inactive → active. Nav2 usa para acender em ordem. |
| **costmap** | Grade 2D com custo por célula. 0 = livre, 254 = obstáculo lethal, intermediários = inflação. |
| **footprint** | Polígono 2D da projeção do robô no chão. Define colisão para o planner. |
| **odometria** | Estimativa de pose pela integração de velocidade/encoders (mecânico: "dead reckoning"). |
| **EKF** | Extended Kalman Filter — funde várias fontes de pose/twist com modelos lineares (mecânico: "estimador de estado"). |
| **AMCL** | Adaptive Monte-Carlo Localisation. Casa scan do LiDAR contra mapa estático para descobrir onde o robô está. |
| **SLAM** | Simultaneous Localisation And Mapping — constrói o mapa enquanto se localiza nele. |
| **MPPI** | Model Predictive Path Integral — controlador local que amostra milhares de trajetórias futuras e escolhe a de menor custo. |
| **SMAC** | Família de planejadores globais do Nav2; `SmacPlannerHybrid` faz A* com primitivas Dubins/Reeds-Shepp. |
| **Behavior tree** | Árvore de decisão hierárquica que orquestra "planejar → seguir → se falhar, recuperar". XML. |

---

## 6. O que ainda **não está** no `rbot` (e a gente precisa adicionar)

- **Garfo elevador** (junta `prismatic` em z). Vai entrar em `robot/rlai_description/urdf/base/fork.urdf.xacro` (novo), com controlador `position_controllers/JointPositionController` em `controllers.yaml`.
- **Lógica de missão pickup→deliver.** Novo pacote `src/rbot/missions/rlai_logistics/`.
- **Mundo Galp real.** Novo `simulation/rlai_gazebo/worlds/galp_amr.sdf` com pallets, doca, expedição. + mapa 2D correspondente em `/workspace/rbot/maps/`.
- **AprilTag docking.** Novo pacote de perception em `src/rbot/perception/rlai_apriltag/` consumindo a câmera RGB-D existente.

Itens prioritários estão em `ROADMAP.md §3 (Falta fazer)`.
