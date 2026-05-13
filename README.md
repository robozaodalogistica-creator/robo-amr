# robo-amr — AMR de pallet para galpão robô-only

> Plataforma de pesquisa & desenvolvimento de um **Autonomous Mobile Robot (AMR)
> de pallet**, projetada para galpões **sem operadores humanos circulando**, com
> foco na PME logística brasileira ainda desatendida pelo mercado.

**Status**: protótipo de software (simulação + stack de navegação funcionando).
Sem hardware físico ainda. **Não é production-ready**.

---

## 1. Visão do produto

Um robô móvel autônomo capaz de transportar pallets dentro de um galpão
**sem pessoas**, com SLAM/Nav2, missões pré-programadas (doca → estoque →
expedição) e operação 24/7.

A tese é estreita de propósito: ambiente robô-only elimina a maior parte do
custo regulatório e do risco de certificação de segurança funcional (ISO 3691-4,
SRP/CS). Sem humanos circulando, **safety scanners** continuam obrigatórios,
mas o sistema não precisa parar para deixar uma pessoa passar, não precisa de
sinalização luminosa para humano, não precisa de UI no robô. Isso muda o
**TCO** e o **payback** o suficiente para PME considerar.

### 1.1 Problema de mercado

- O mercado brasileiro de PME logística (3PL pequenos, distribuidores, e-commerce
  regional) é **desatendido**: as ofertas são empilhadeiras autônomas importadas
  (Toyota, Linde, Jungheinrich) a 6 dígitos de USD, ou nada.
- A maior parte desses operadores aceita reorganizar o layout do galpão se isso
  baratear o robô. Eles **não exigem** convivência humano-robô.
- Não existe player nacional com produto AMR de pallet competitivo (até onde
  apuramos). Existe demanda reprimida.

### 1.2 Hipótese de produto

Um AMR de pallet **robô-only**, projeto enxuto, com:

- Diferencial simples (2 rodas tracionadas + casters).
- LiDAR 2D + IMU + encoders. Sem visão para começar.
- Capacidade de 600–1000 kg por viagem.
- Garfo elevatório passivo (sobe/desce, não inclina).
- Stack ROS 2 + Nav2 sobre Linux nativo.
- Preço-alvo: ordem de grandeza inferior ao do importado.

---

## 2. Estado atual (o que funciona hoje)

Tudo é **simulação**. Não há hardware. O que está pronto:

| Subsistema | Status | Onde |
|---|---|---|
| Loop cinemático do robô (`/cmd_vel` → odom/tf) | ✅ funciona | [`amr_pallet/src/amr_pallet/amr_pallet/robot_sim.py`](amr_pallet/src/amr_pallet/amr_pallet/robot_sim.py) |
| Mundo Gazebo de galpão (20×15 m, 4 pallets, doca, expedição) | ✅ visível no GUI | [`amr_pallet/src/amr_pallet/worlds/galp_amr.world`](amr_pallet/src/amr_pallet/worlds/galp_amr.world) |
| Mapa 2D do galpão (occupancy grid) | ✅ carrega | [`amr_pallet/src/amr_pallet/maps/warehouse.yaml`](amr_pallet/src/amr_pallet/maps/warehouse.yaml) |
| Nav2 completo (planner, controller DWB, BT, costmaps, smoother) | ✅ navega | [`amr_pallet/src/amr_pallet/config/nav2_params.yaml`](amr_pallet/src/amr_pallet/config/nav2_params.yaml) |
| Missão logística (4 pallets, doca↔expedição) | ✅ roda autônoma | [`amr_pallet/src/amr_pallet/amr_pallet/logistics_mission.py`](amr_pallet/src/amr_pallet/amr_pallet/logistics_mission.py) |
| Foxglove bridge (WebSocket :8765) | ✅ funciona | dentro do launch |
| Streaming do Gazebo via navegador (Xvfb + VNC + cloudflared) | ✅ funciona | [`start_gui.sh`](start_gui.sh) + [`start_amr_gui.sh`](start_amr_gui.sh) |
| Setup do ambiente (ROS 2 Jazzy + Gazebo + Nav2 + Claude Code) | ✅ idempotente | [`setup_master.sh`](setup_master.sh) |

**O que NÃO funciona / não existe** (lista resumida — detalhe em
[`docs/ROBOT_ANALYSIS.md`](docs/ROBOT_ANALYSIS.md)):

- ❌ Modelo dinâmico (massa, inércia, motor, atrito) — robô é cinemático puro.
- ❌ LiDAR de verdade — o `/scan` é fake (sempre "campo livre", `inf` em todos
  os raios). O Nav2 navega **sem ver obstáculos dinâmicos**.
- ❌ URDF — só existe SDF cosmético para visualização.
- ❌ SLAM real (mapa é fornecido pronto).
- ❌ AMCL (a transformação `map→odom` é identidade fixa).
- ❌ Garfo elevatório (a missão "coleta" pallets sem nada físico acontecer).
- ❌ Hardware.

---

## 3. Stack tecnológica

| Camada | Escolha | Por quê (resumo — detalhe em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)) |
|---|---|---|
| SO base | **Ubuntu 24.04 LTS** | É a base oficial do Jazzy. |
| ROS | **ROS 2 Jazzy Jalisco** | LTS atual (suporte até maio/2029). Humble (22.04) já está em fim de vida útil para greenfield. |
| Simulador | **Gazebo Harmonic** | Par oficial do Jazzy. Sucessor do Ignition; ODE como física, Ogre2 como render. |
| Navegação | **Nav2** (BT navigator, DWB, NavFn, SmacPlanner disponível) | Stack-padrão de fato da comunidade ROS 2. |
| Mapeamento | **slam_toolbox** (instalado, ainda não usado) | Idem. |
| Mensagens DDS | **CycloneDDS** (`rmw_cyclonedds_cpp`) | Mais estável que o Fast-DDS default em Jazzy para LAN única. |
| Visualização | **Foxglove Studio** (via `foxglove_bridge`) + **RViz2** | Foxglove abre no navegador; útil para PC do sócio sem precisar instalar nada. |
| Streaming do GUI (no RunPod) | **Xvfb + x11vnc + noVNC + cloudflared** | Quando precisar acessar o Gazebo gráfico rodando no container. |
| Linguagens | **Python 3.12** (toda a stack atual) + C++ disponível | Python só onde performance não é gargalo. |

---

## 4. Roadmap das próximas fases

Ordem geral: **simulação realista → hardware**. Cada fase amadurece o software
o suficiente para que o próximo passo faça sentido.

Detalhes técnicos e localização exata dos parâmetros em
[`docs/ROBOT_ANALYSIS.md §9`](docs/ROBOT_ANALYSIS.md#9-próximas-modificações-possíveis).

### Fase 1 — Sensoriamento real em simulação (1-2 semanas)

Tirar o robô da fantasia de software.

- Sensor `<gpu_lidar>` no `model.sdf` substituindo o LaserScan fake — o Nav2
  passa a ver paredes/pallets de verdade.
- IMU no `base_link` (o plugin Gazebo já está carregado).
- Bridge `ros_gz_bridge` real para `/scan`, `/odom`, `/imu/data`, `/clock`.
- Footprint retangular (0.50 × 0.40) no Nav2 em vez do disco r=0.25.

Critério de pronto: missão dos 4 pallets continua funcionando, mas agora com
costmap local refletindo o mundo.

### Fase 2 — Modelo dinâmico (1-2 semanas)

Substituir o robô-fantasma por um diferencial físico.

- URDF/xacro completo (base_link, rodas com `<joint type="continuous">`,
  4 casters, sensores).
- Plugin `gz-sim-diff-drive-system` em vez do `robot_sim.py`.
- Calibrar massa, inércia, atrito até o robô seguir o `/cmd_vel` sem capotar.
- Aposentar o `gz_pose_bridge.py` (teleporte).

Critério de pronto: TF tree gerada pelo `robot_state_publisher`, dinâmica
emergente do `cmd_vel`, missão continua funcionando.

### Fase 3 — SLAM e localização (1 semana)

- `slam_toolbox` em modo async para mapear o galpão a partir do `/scan` real.
- `nav2_amcl` para localização após o mapa pronto.
- Remover a TF `map→odom` identidade.

Critério de pronto: robô consegue ser solto numa pose desconhecida e se
localizar, e consegue mapear um galpão novo.

### Fase 4 — Manipulação de pallet (1-2 semanas)

- Garfo elevatório como `<joint type="prismatic">` (curso 0–0.15 m).
- Plugin `joint_position_controller` para subir/descer.
- Anexar/desanexar pallets via `gz service` durante a missão.
- Footprint dinâmico no Nav2 (vazio vs carregando).

Critério de pronto: missão pega o pallet de verdade no Gazebo, anda com ele
(inércia maior), entrega.

### Fase 5 — Multi-robô e orquestração (multi-dia)

- Spawnar N robôs com namespaces.
- Orquestrador central que reparte missões e evita deadlocks de corredor.
- Avaliar OpenRMF.

### Fase 6 — Hardware (escopo aberto)

Decisões em aberto: chassis, motores (servo BLDC vs DC com encoder),
controlador (PLC vs micro), LiDAR (modelo/fornecedor), bateria.

A simulação madura das fases 1-4 é o que reduz risco aqui — o software roda
igual no robô real (mudando só os drivers de hardware).

---

## 5. Links rápidos

- 📐 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — componentes, decisões de
  stack, limitações conhecidas.
- 🚀 [`docs/ONBOARDING.md`](docs/ONBOARDING.md) — setup do ambiente no seu PC
  ou no RunPod, primeiros comandos, primeiros experimentos.
- 🔬 [`docs/ROBOT_ANALYSIS.md`](docs/ROBOT_ANALYSIS.md) — análise técnica do que
  o "robô" é hoje (cinemático puro, sem física, LiDAR fake), com localização
  exata de cada parâmetro e lista priorizada de modificações.
- 🛠️ [`setup_master.sh`](setup_master.sh) — provisionamento idempotente (ROS 2
  Jazzy + Gazebo + Nav2 + Claude Code) — usado no container RunPod.

---

## 6. Estrutura do repositório

```
/workspace
├── README.md                  ← este arquivo
├── docs/
│   ├── ARCHITECTURE.md        ← decisões de stack
│   ├── ONBOARDING.md          ← guia para começar
│   └── ROBOT_ANALYSIS.md      ← análise técnica do robô atual
├── amr_pallet/                ← workspace principal (ROS 2 + Gazebo + Nav2)
│   └── src/amr_pallet/
│       ├── amr_pallet/        ← nodes Python (robot_sim, logistics_mission)
│       ├── config/            ← nav2_params.yaml
│       ├── launch/            ← warehouse.launch.py
│       ├── maps/              ← occupancy grids
│       ├── models/            ← SDF do amr_viz
│       └── worlds/            ← galp_amr.world
├── nav_test/                  ← workspace de testes Nav2 (TB3-based)
├── tb3_nav_demo/              ← demo TurtleBot3 (5 waypoints)
├── openamrobot/               ← clone do projeto upstream (referência — ver ARCHITECTURE.md)
├── setup_master.sh            ← provisionamento idempotente
├── start_gui.sh               ← Xvfb + VNC + tunel (acesso navegador)
├── start_amr_gui.sh           ← sobe Gazebo + Nav2 + missão
└── install_ros2_*.sh          ← scripts auxiliares de instalação
```

---

## 7. Quem está no projeto

- **Você** — sócio programador (este onboarding é para você).
- O outro sócio — engenheiro mecânico, trabalha no RunPod, foco em
  modelagem/física do robô.

Comunicação técnica: este README + os três docs em `docs/` são a fonte da
verdade. Mudou de ideia em algo arquitetural — atualize aqui.
