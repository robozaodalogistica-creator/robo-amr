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

## 2. Como funciona o desenvolvimento desse tipo de robô

### A realidade: ninguém constrói AMR do zero

> [!CAUTION]
> Construir um AMR completo do zero é tecnicamente impossível para uma empresa pequena. Mesmo gigantes (Toyota, KUKA, Geek+) não fazem.

A indústria toda funciona por integração de componentes:

- 📦 **Hardware**: chassi, motores, sensores, computador — compra-se pronto
- 💻 **Software base**: ROS 2, Nav2, Gazebo, SLAM — open source
- 🔧 **URDF do robô**: descrição mecânica — modela-se em CAD ou adota-se um existente
- 🎯 **Lógica específica**: missão, interface, integração com cliente — programa-se sob medida

### O que JÁ existe pronto (e usamos)

| Componente | Origem | O que faz |
|---|---|---|
| ROS 2 Jazzy | Open Robotics Foundation | SO do robô — pub/sub, lifecycle, TF, launchers |
| Nav2 | Comunidade ROS (Steve Macenski et al.) | Navegação autônoma — planner global, controller local, behavior tree |
| SLAM Toolbox | Steve Macenski (Samsung) | Mapeamento 2D online e lifelong |
| Gazebo Harmonic | Open Robotics | Simulação física |
| ros2_control | Comunidade ROS | Controle de baixo nível — diff_drive_controller, 100 Hz |
| EKF + AMCL + Madgwick | robot_localization / nav2_amcl | Localização fundida (IMU + odom + LiDAR) |
| Drivers de sensores | Slamtec, Velodyne, Intel | Comunicação com hardware real |
| rbot | Black Coffee Robotics (Apache 2.0) | Robô de referência — URDF, ros2_control, EKF, AMCL, SLAM e Nav2 já integrados |

> [!WARNING]
> Tentar reescrever ROS 2, Nav2 ou Gazebo seria perder anos de trabalho. **Não fazemos.**

### O que NÓS precisamos PROJETAR

1. **Mecânica do robô específico** — Sob medida para PME brasileira
   - Chassi (tamanho, material, capacidade de carga)
   - Garfo elevador (mecanismo, curso, sensores de presença)
   - Bateria (autonomia, recarga)
   - Layout: onde fica cada sensor, peso distribuído

2. **CAD em SolidWorks** que se torne URDF do simulador

3. **Características operacionais do galpão alvo**
   - Largura de corredor mínima
   - Carga máxima por viagem
   - Velocidade econômica
   - Footprint para Nav2

### O que NÓS precisamos PROGRAMAR

1. **URDF customizado** (~200 linhas)
2. **Lógica de missão logística** — Receber ordem → buscar pallet → entregar → voltar (~300-500 linhas Python)
3. **Integração com WMS do cliente** — REST API ou conector SAP/Oracle/Manhattan (~500-1000 linhas por cliente)
4. **Garfo elevador** — Plugin Gazebo + lógica de ativação (~150 linhas)
5. **Interface de operação** — Dashboard web para operador (~1000-2000 linhas)
6. **Sistema de detecção de pallet** — AprilTag + visão computacional (~200 linhas)

### O que NÓS precisamos CONFIGURAR

> [!TIP]
> Configuração é diferente de programar. São arquivos YAML que dizem ao software pronto como se comportar.

- `nav2_params.yaml` — parâmetros de navegação
- `controller_manager.yaml` — limites de motor
- `slam_params.yaml` — comportamento do mapeamento
- `ekf.yaml` — fusão sensorial

**Calibrar bem essas configurações é onde está boa parte do diferencial técnico.**

### Resumindo: quanto do projeto é nosso

| Camada | Origem | % do projeto |
|---|---|---|
| Sistema operacional | Open source | 0% nosso |
| Algoritmos de navegação | Open source | 0% nosso |
| Simulador | Open source | 0% nosso |
| Drivers de hardware | Fabricantes | 0% nosso |
| URDF base | rbot adotado | 30% nosso (custom) |
| Configurações YAML | Nós ajustamos | 100% nosso |
| Lógica de missão | Nós programamos | 100% nosso |
| Mecânica física | Nós projetamos | 100% nosso |
| Integração WMS | Nós fazemos | 100% nosso |

> [!IMPORTANT]
> Total: ~15% código novo, 100% integração. Esse é o modelo que TODAS as empresas de AMR sérias seguem no mundo.

### Por que isso não é desvantagem

Empresas que seguem esse caminho:

- ✅ Toyota Material Handling (BT, Raymond) — usa ROS no R&D
- ✅ Locus Robotics — começou com ROS
- ✅ 6 River Systems — ROS
- ✅ Fetch Robotics — ROS
- ✅ Geek+ — base ROS modificada

A vantagem competitiva NÃO está em "reinventar a roda". Está em:

- 🎯 **Foco no nicho certo** — galpão robô-only para PME no Brasil
- 🎯 **Mecânica robusta** — hardware confiável e barato
- 🎯 **Integração** — fazer tudo funcionar junto, sem buracos
- 🎯 **Atendimento** — suporte rápido, peças disponíveis
- 🎯 **Preço acessível** — viável para PME, não só para Amazon

---

## 3. Estado do nosso projeto

### ✅ O que funciona hoje

- Robô `rbot` adotado com URDF/Xacro completo e física real
- Modelo dinâmico: massa, inércia, joints, atrito
- LiDAR 2D + 3D fazendo raycast real
- IMU 200 Hz, câmera RGB-D, câmera estéreo, GPS
- `ros2_control` + diff-drive plugin
- SLAM Toolbox + AMCL + EKF (localização completa)
- Nav2 estado-da-arte (SMAC Hybrid-A* + MPPI)
- Gazebo Harmonic + ROS 2 Jazzy
- Visualização VNC funcional
- GitHub sincronizado

**Validado**: goal `NavigateToPose` no `small_warehouse` — todos os lifecycle nodes ACTIVE, robô navegou e parou no goal com SUCCEEDED.

Detalhes técnicos completos em [`docs/RBOT_ANALYSIS.md`](docs/RBOT_ANALYSIS.md).

### 🚧 O que falta fazer

> [!WARNING]
> Próximas entregas para virar AMR de pallet completo:

| Falta | Por quê | Onde vai entrar |
|---|---|---|
| 🔧 **Garfo elevador** (junta prismatic em Z, curso 0.0–0.20 m) | rbot é robô móvel genérico — não tem mecanismo de elevação | `src/rbot/robot/rlai_description/urdf/base/fork.urdf.xacro` |
| 🏭 **Mundo galpão Galp** (pallets, doca, expedição) | rbot traz mundos genéricos; cliente-âncora tem layout próprio | `src/rbot/simulation/rlai_gazebo/worlds/galp_amr.sdf` |
| 📦 **Missão logística** (state machine pickup → transit → drop) | rbot só faz NavigateToPose solto | `src/rbot/missions/rlai_logistics/` |
| 🎯 **Docking de pallet por AprilTag** | Alinhamento fino (±2 cm) com câmera RGB-D | `src/rbot/perception/rlai_apriltag/` (pacote novo) |
| 🗺️ **Mapa 2D do galpão Galp** | Gerar via SLAM e salvar para AMCL | `/workspace/rbot/maps/galp_amr.yaml` |
| 🤖 **Multi-robô (fleet)** | Namespaces ROS + semáforo de zona | A definir |
| 🛠️ **Hardware** | Chassi, motores, encoders, bateria, PCB | Fase posterior |

Itens priorizados em [`ROADMAP.md`](ROADMAP.md).

---

## 4. Stack tecnológica

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

## 5. Quickstart

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

## 6. Estrutura do repositório

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

## 7. Roadmap das próximas fases

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

## 8. Documentação relacionada

- 📐 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — decisões de stack, limitações conhecidas.
- 🚀 [`docs/ONBOARDING.md`](docs/ONBOARDING.md) — setup do ambiente, primeiros comandos.
- 🧭 [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) — guia pedagógico do código `src/rbot/`: camadas + "onde muda o quê" (para engenheiros mecânicos).
- 🔬 [`docs/RBOT_ANALYSIS.md`](docs/RBOT_ANALYSIS.md) — análise técnica completa do rbot adotado.
- 📜 [`docs/ROBOT_ANALYSIS.md`](docs/ROBOT_ANALYSIS.md) — análise do protótipo `amr_pallet` anterior (histórico).
- 🗺️ [`ROADMAP.md`](ROADMAP.md) — planejamento vivo, decisões com data.
- 🧾 [`NOTICE.md`](NOTICE.md) + [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) — atribuição e licenças.

---

## 9. Quem está no projeto

- **Sócio engenheiro mecânico** — foco em modelagem física do robô, CAD, decisões de hardware. Trabalha no RunPod com VNC.
- **Sócio programador** — foco em software, infra, integração.

Comunicação técnica: este README + os docs em `docs/` + o `ROADMAP.md` são
a fonte da verdade. Mudou de ideia em algo arquitetural — atualize aqui.
