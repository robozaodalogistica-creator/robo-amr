# robo-amr — AMR de pallet para galpão robô-only

> Plataforma de pesquisa & desenvolvimento de um **Autonomous Mobile Robot
> (AMR) de pallet**, projetada para galpões **sem operadores humanos
> circulando**, com foco na PME logística brasileira ainda desatendida pelo
> mercado.

---

## 🎉 Marco — 2026-05-13

**O `rbot` foi adotado como base do projeto.** Pulamos ~4 meses de
desenvolvimento que teríamos para construir do zero o que ele já entrega:
URDF físico real, ros2_control com diff-drive de torque, 6 sensores
simulados, EKF + AMCL, SLAM Toolbox e Nav2 estado-da-arte (SMAC Hybrid-A*
+ MPPI).

Código importado para [`src/rbot/`](src/rbot/) sob Apache 2.0, com
atribuição em [`NOTICE.md`](NOTICE.md) e
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). A partir daqui
modificamos livremente para o caso de uso AMR-de-pallet em galpão
robô-only e portamos nossa lógica de missão por cima do esqueleto do rbot.

Análise técnica completa do que herdamos: [`docs/RBOT_ANALYSIS.md`](docs/RBOT_ANALYSIS.md).
Decisão registrada em [`ROADMAP.md §6 #003`](ROADMAP.md).

---

## 1. Visão do produto

Um robô móvel autônomo capaz de transportar pallets dentro de um galpão
**sem pessoas**, com SLAM/Nav2, missões pré-programadas (doca → estoque →
expedição) e operação 24/7.

A tese é estreita de propósito: ambiente robô-only elimina a maior parte
do custo regulatório e do risco de certificação de segurança funcional
(ISO 3691-4, SRP/CS). Sem humanos circulando, o sistema não precisa parar
para deixar uma pessoa passar, não precisa de sinalização para humano,
não precisa de UI no robô. Isso muda o **TCO** e o **payback** o suficiente
para PME considerar.

Mercado-alvo: PMEs brasileiras de logística (3PL pequenos, distribuidores,
e-commerce regional) que hoje não pagam US$ 50–150k por unidade dos
fornecedores importados (Toyota, Linde, Jungheinrich, Geek+, KION). Não
exigem convivência humano-robô e topam reorganizar o layout se isso
baratear o robô.

---

## 2. Estado atual

### ✅ O que funciona hoje

| Item | Onde |
|---|---|
| ✅ **Robô `rbot` adotado** — URDF/Xacro completo, física real | [`src/rbot/robot/rlai_description/urdf/`](src/rbot/robot/rlai_description/urdf/) |
| ✅ **Modelo dinâmico real** — massa, tensores de inércia, joints `continuous` nas rodas, atrito | `src/rbot/robot/rlai_description/urdf/base/` |
| ✅ **LiDAR 2D** (RPLIDAR A3, 720 raios, 15 Hz) — raycast real do Gazebo | `src/rbot/robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro` |
| ✅ **LiDAR 3D** (Velodyne VLP-16, 10 Hz) — opt-in via `lidar_3d_enabled:=true` | idem |
| ✅ **IMU 200 Hz** com filtro Madgwick → orientação fundida pelo EKF | `src/rbot/robot/rlai_description/urdf/sensors/imu.urdf.xacro` |
| ✅ **Câmera RGB-D Intel D435i** — `/depth_camera/depth` e `/depth_camera/image_raw` 30 Hz | `src/rbot/robot/rlai_description/urdf/sensors/depth_camera.urdf.xacro` |
| ✅ **Câmera estéreo** (opt-in) | `src/rbot/robot/rlai_description/urdf/sensors/stereo_camera.urdf.xacro` |
| ✅ **GPS** (opt-in, navsat) + **ground truth** disponível | `src/rbot/robot/rlai_description/urdf/sensors/gps.urdf.xacro` |
| ✅ **`ros2_control` + diff-drive plugin** — controle por velocidade nos joints, odometria pelas rodas | `src/rbot/control/rlai_control/config/controllers.yaml` |
| ✅ **SLAM Toolbox** — modos `online_async` e `lifelong` configurados | `src/rbot/mapping/rlai_mapping/config/` |
| ✅ **AMCL** para localização global em mapa estático | `src/rbot/localization/rlai_localization/config/amcl.yaml` |
| ✅ **EKF (`robot_localization`)** — fusão IMU + odom → `odom → base_footprint` | `src/rbot/localization/rlai_localization/config/ekf.yaml` |
| ✅ **Nav2 estado-da-arte** — **SMAC Hybrid-A*** (planner global) + **MPPI** (controller local) + behavior tree + waypoint follower | `src/rbot/navigation/rlai_navigation/config/nav2_params.yaml` |
| ✅ **Gazebo Harmonic + ROS 2 Jazzy** — `colcon build` OK, simulação roda | `setup_master.sh` |
| ✅ **Visualização VNC** — `DISPLAY=:1` + Xvfb + x11vnc + cloudflared. URL pública em `/tmp/gui_stream/public_url` | `start_gui.sh` |
| ✅ **GitHub sincronizado** — `origin/main` em [github.com/robozaodalogistica-creator/robo-amr](https://github.com/robozaodalogistica-creator/robo-amr) |

Validado em runtime: goal `NavigateToPose` enviado para o robô no
`small_warehouse`, todos os 9 lifecycle nodes do Nav2 + AMCL + map_server
em estado `ACTIVE`, robô navegou e parou no goal com `error_code=0`
(`SUCCEEDED`). Detalhes em [`docs/RBOT_ANALYSIS.md`](docs/RBOT_ANALYSIS.md).

### 🚧 O que falta fazer

Para virar **AMR de pallet de galpão de verdade**, ainda precisamos:

| Falta | Por quê | Onde vai entrar |
|---|---|---|
| 🔧 **Garfo elevador** (junta `prismatic` em z, curso 0.0–0.20 m) | rbot é um robô móvel genérico — **não tem mecanismo de elevação**. É trabalho nosso. | `src/rbot/robot/rlai_description/urdf/base/fork.urdf.xacro` (novo) + `controllers.yaml` (`position_controllers/JointPositionController`) |
| 🏭 **Mundo galpão Galp** (pallets, doca, expedição) | rbot traz `small_warehouse`/`office_floor` genéricos. Precisamos do nosso layout. | Portar `galp_amr.world` do antigo `amr_pallet` para `src/rbot/simulation/rlai_gazebo/worlds/` |
| 📦 **Missão logística** (state machine pickup → transit → drop) | rbot só faz `NavigateToPose` solto. Lógica de missão é nossa. | Portar `logistics_mission` do antigo `amr_pallet` para `src/rbot/missions/rlai_logistics/` (novo pacote) |
| 🎯 **Docking de pallet por AprilTag** | Alinhamento fino (±2 cm) antes de elevar o garfo. Câmera RGB-D já existe; falta o pipeline. | `src/rbot/perception/rlai_apriltag/` (novo) — pacote `apriltag_ros` no Jazzy |
| 🗺️ **Mapa 2D do galpão Galp** | Gerar via SLAM rodando contra o novo mundo, salvar para AMCL. | `/workspace/rbot/maps/galp_amr.yaml` (novo) |
| 🤖 **Multi-robô (fleet)** | 2–3 robôs com namespaces ROS + coordenação básica de zona. Antes de OpenRMF. | A definir |
| 🛠️ **Hardware** | Tudo é simulação. Chassi, motores, encoders, bateria, PCB. | Fase posterior |

Itens detalhados e priorizados em [`ROADMAP.md §3`](ROADMAP.md).

---

## 3. Stack tecnológica

| Camada | Escolha | Notas |
|---|---|---|
| SO base | **Ubuntu 24.04 LTS** | Base oficial do Jazzy |
| ROS | **ROS 2 Jazzy Jalisco** | LTS atual (suporte até maio/2029) |
| Simulador | **Gazebo Harmonic (gz-sim 8.x)** | Par oficial do Jazzy. SDFormat 1.11 |
| URDF | **xacro** (macros) | Pacotes em `src/rbot/robot/rlai_description/` |
| Controle baixo nível | **`ros2_control`** + `diff_drive_controller` + `joint_state_broadcaster` + `velocity_smoother` | 100 Hz update rate |
| Localização | **`robot_localization` EKF** + **`nav2_amcl`** + **`imu_filter_madgwick`** | EKF: odom + IMU → `odom→base_footprint`. AMCL → `map→odom` |
| Mapeamento | **`slam_toolbox`** (`online_async`, `lifelong`) | Resolução 5 cm |
| Navegação | **Nav2** — `SmacPlannerHybrid` (planner) + `MPPIController` (controller) + `SimpleSmoother` + `BehaviorTree.CPP` | Footprint retangular 0.50×0.40 m + 3 cm padding |
| Perception (sim) | `rlai_camera_processing` (rectify + disparity + depth point cloud) + `rlai_lidar_processing` | C++ |
| DDS | **CycloneDDS** (`rmw_cyclonedds_cpp`) | Mais estável que Fast-DDS em Jazzy para LAN única |
| Visualização | **RViz2** + **Foxglove Studio** (via `foxglove_bridge`) | Foxglove abre no navegador |
| Streaming GUI | **Xvfb + x11vnc + noVNC + cloudflared** | Para Gazebo gráfico no container RunPod |
| Linguagens | **Python 3.12** + **C++** | C++ para perception, Python para missão/launch |

Decisões registradas em [`ROADMAP.md §6`](ROADMAP.md) e
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 4. Quickstart

Pré-requisito: workspace já buildado (`colcon build` em `/workspace/rbot/`,
feito pelo `setup_master.sh`). Para o novo workspace `src/rbot/` adotado,
rodar `colcon build --packages-up-to rlai_bringup rlai_navigation` quando
quiser usar a cópia em vez do clone original.

```bash
# Sobe VNC + cloudflared (se ainda não estiver rodando)
bash /workspace/start_gui.sh

# Aponta o ambiente para o workspace do rbot
source /workspace/rbot/install/setup.bash
export DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1 \
       GZ_SIM_RESOURCE_PATH=/workspace/rbot/install/rlai_gazebo/share/rlai_gazebo:/workspace/rbot/install/rlai_meshes/share

# Sobe Gazebo + robô + EKF + AMCL (map padrão)
ros2 launch rlai_bringup simulation.launch.py \
    use_amcl:=true \
    map_yaml_file:=/workspace/rbot/maps/my_map.yaml \
    world:=small_warehouse &

# Em outra aba: sobe Nav2
ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true &

# Em outra aba: manda goal de teste (2 m à frente)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 3.0, y: 1.0}, orientation: {w: 1.0}}}}" \
  --feedback
```

URL do VNC: `cat /tmp/gui_stream/public_url`.

Setup completo do ambiente do zero: [`docs/ONBOARDING.md`](docs/ONBOARDING.md).

---

## 5. Estrutura do repositório

```
/workspace
├── README.md                    ← este arquivo
├── ROADMAP.md                   ← roadmap vivo, decisões e prioridades
├── NOTICE.md                    ← atribuição do rbot (Apache 2.0)
├── THIRD_PARTY_LICENSES.md      ← obrigações de licença
│
├── docs/
│   ├── ARCHITECTURE.md          ← decisões de stack
│   ├── ONBOARDING.md            ← setup do zero (RunPod ou PC local)
│   ├── CODE_GUIDE.md            ← guia pedagógico do código rbot (camadas + "onde muda o quê")
│   ├── RBOT_ANALYSIS.md         ← análise técnica do rbot adotado
│   └── ROBOT_ANALYSIS.md        ← análise técnica do amr_pallet anterior (histórico)
│
├── src/
│   └── rbot/                    ← BASE ADOTADA (Apache 2.0 — ver NOTICE.md)
│       ├── LICENSE              ← Apache 2.0 upstream preservada
│       ├── bringup/             ← top-level launch (simulation.launch.py)
│       ├── control/             ← ros2_control + velocity_smoother
│       ├── localization/        ← EKF + AMCL + Madgwick
│       ├── mapping/             ← SLAM Toolbox
│       ├── navigation/          ← Nav2 (SMAC + MPPI + BT)
│       ├── perception/          ← stereo, depth, lidar processing (C++)
│       ├── robot/               ← URDF/xacro + meshes
│       ├── simulation/          ← Gazebo worlds, modelos, launches
│       └── utils/
│
├── rbot/                        ← clone upstream (referência; não rastreado pelo nosso git)
├── amr_pallet/                  ← protótipo anterior (histórico — ver ROBOT_ANALYSIS.md)
├── nav_test/, tb3_nav_demo/     ← demos auxiliares
├── openamrobot/                 ← referência externa
│
├── setup_master.sh              ← provisionamento idempotente (ROS 2 Jazzy + Gazebo + Nav2)
├── start_gui.sh                 ← Xvfb + x11vnc + noVNC + cloudflared
├── start_amr_gui.sh             ← sobe Gazebo + Nav2 (referência do antigo amr_pallet)
└── install_ros2_*.sh            ← scripts auxiliares
```

---

## 6. Roadmap das próximas fases

> Sintetizado a partir de [`ROADMAP.md`](ROADMAP.md). Veja lá os critérios
> de aceitação detalhados.

| Fase | Foco | Status |
|---|---|---|
| **0** | Adotar rbot como base | ✅ Concluído (2026-05-13) |
| **1** | Portar mundo Galp + missão logística + adicionar garfo elevador | 🟡 Em curso |
| **2** | AprilTag docking de pallet (alinhamento fino ±2 cm) | ⏸ Próximo |
| **3** | SLAM operacional contra o mundo Galp real + mapa salvo para AMCL | ⏸ Próximo |
| **4** | Multi-robô básico (fleet 2-3 unidades, namespaces, semáforo de zona) | ⏸ Backlog |
| **5** | CAD mecânico (SolidWorks), BOM, inércias do CAD para URDF | ⏸ Backlog |
| **6** | Hardware (chassi, motorredutores, encoders, BMS, controlador) | ⏸ Backlog |

---

## 7. Documentação relacionada

- 📐 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — decisões de stack, limitações conhecidas.
- 🚀 [`docs/ONBOARDING.md`](docs/ONBOARDING.md) — setup do ambiente, primeiros comandos.
- 🧭 [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) — guia pedagógico do código `src/rbot/`: camadas + "onde muda o quê" (para engenheiros mecânicos).
- 🔬 [`docs/RBOT_ANALYSIS.md`](docs/RBOT_ANALYSIS.md) — análise técnica completa do rbot adotado.
- 📜 [`docs/ROBOT_ANALYSIS.md`](docs/ROBOT_ANALYSIS.md) — análise do protótipo `amr_pallet` anterior (histórico).
- 🗺️ [`ROADMAP.md`](ROADMAP.md) — planejamento vivo, decisões com data.
- 🧾 [`NOTICE.md`](NOTICE.md) + [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) — atribuição e licenças.

---

## 8. Quem está no projeto

- **Sócio engenheiro mecânico** — foco em modelagem física do robô, CAD, decisões de hardware. Trabalha no RunPod com VNC.
- **Sócio programador** — foco em software, infra, integração.

Comunicação técnica: este README + os docs em `docs/` + o `ROADMAP.md` são
a fonte da verdade. Mudou de ideia em algo arquitetural — atualize aqui.
