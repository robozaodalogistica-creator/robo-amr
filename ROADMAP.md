# Roadmap — AMR Pallet Galp

> **Documento vivo de planejamento.** Atualize sempre que decidir algo.
> Última atualização: 2026-05-14 (modo didático concluído)

---

## 1. Visão do produto

**AMR de pallet para galpão robô-only no Brasil, foco em PME.** Construímos um robô móvel autônomo de baixo custo para movimentação de pallets em galpões logísticos sem presença humana durante operação ("robô-only" — turnos noturnos, áreas restritas, dark warehouses). Mercado-alvo: pequenas e médias empresas brasileiras de logística e distribuição, que hoje não conseguem pagar AGV/AMR de fornecedores estrangeiros (Geek+, KION, Toyota) que custam US$ 50–150k por unidade. Diferenciais: stack 100% open source (ROS 2 Jazzy + Nav2), simulação realista antes de hardware, modo "robô-only" formalizado (dispensa toda a complexidade e custo de detecção/segurança humana).

---

## 2. Estado atual

**Marco**: o `rbot` foi adotado como base do projeto (ver Decisão #003, §6).
Código vive em `src/rbot/` sob Apache 2.0 com atribuição em `NOTICE.md` e
`THIRD_PARTY_LICENSES.md`. Detalhes técnicos em `docs/RBOT_ANALYSIS.md`;
referência do protótipo anterior em `docs/ROBOT_ANALYSIS.md`.

**O que funciona hoje**:

| Componente | Status atual | Observação |
|---|---|---|
| Workspace ROS 2 Jazzy | ✅ Instalado e funcionando | `setup_master.sh` reinstala em ~10 min |
| Gazebo Harmonic | ✅ GUI streamada via VNC (`DISPLAY=:1`) | Cloudflared expõe URL pública em `/tmp/gui_stream/public_url` |
| `rbot` adotado como base | ✅ `colcon build` OK, robô rodando no Gazebo | URDF real com física (massa, inércia), 6 sensores, diff-drive por torque |
| Robô na simulação | ✅ Gazebo + spawn + controllers ativos | `rlai_bot` spawned em `small_warehouse`, `diff_drive_controller` e `joint_state_broadcaster` ativos |
| Sensores | ✅ LiDAR 2D + IMU + RGB-D + diff-drive feedback publicando | Câmera estéreo, LiDAR 3D, GPS disponíveis (opt-in via launch args) |
| Localização | ✅ EKF (`robot_localization`) + AMCL ativos | EKF funde IMU + odom; AMCL provê `map→odom` |
| Mapping | ✅ SLAM Toolbox `online_async` no `rbot` (launch pronto) | Ainda não rodado contra mundo definitivo |
| Nav2 (estado-da-arte) | ✅ Lifecycle todo `ACTIVE` | SMAC Hybrid-A* (planner) + MPPI (controller) + behavior tree + waypoint follower; goal `NavigateToPose` testado SUCCEEDED |
| Stack completa | ✅ ROS 2 Jazzy + Gazebo Harmonic + Nav2 + SLAM Toolbox + EKF + AMCL | Tudo no mesmo workspace, sobe via `ros2 launch rlai_bringup simulation.launch.py` + `rlai_navigation navigation.launch.py` |
| Documentação | ✅ `ARCHITECTURE.md`, `ONBOARDING.md`, `ROBOT_ANALYSIS.md`, `RBOT_ANALYSIS.md`, `NOTICE.md`, `THIRD_PARTY_LICENSES.md`, `README.md` |

**Lacunas atuais** (o que falta para virar empilhadeira AMR de galpão):
1. **Sem garfo elevador** (junta `prismatic`) — robô anda, não levanta nada. Não tem em `rbot`; precisa ser adicionado por nós.
2. **Sem mundo Galp modelado** — `rbot` traz `small_warehouse`/`office_floor`; precisamos portar `galp_amr.world` (pallets, doca, expedição) do antigo `amr_pallet`.
3. **Sem missão logística** — `logistics_mission` (estado pickup → transit → drop) ainda no antigo `amr_pallet`; precisa ser portada por cima do rbot.
4. **Sem docking de pallet** (AprilTag/visão) — alinhamento fino antes de elevar o garfo (±2 cm).
5. **Sem fleet** — operação multi-robô e coordenação de zona ainda não modeladas.

---

## 3. Objetivos atuais (próximas 2 semanas)

> **Foco**: portar nossa lógica de pallet/missão por cima do esqueleto do `rbot`
> e fechar a primeira missão pickup→deliver simulada.

### Já temos (herdado do `rbot` adotado)

- [x] **Decisão de base**: adotar `rbot` como esqueleto — Decisão #003, §6.
- [x] **URDF real do robô com física** — massa, tensores de inércia, joints `continuous` para rodas, `fixed` para sensores. Em `src/rbot/robot/rlai_description/`.
- [x] **LiDAR funcionando (raycast real)** — `gpu_lidar` plugin do Gazebo Harmonic publicando `/scan`. LiDAR 2D + LiDAR 3D (opt-in) disponíveis.
- [x] **Plugin diff-drive** — `gz_ros2_control` + `diff_drive_controller` do `ros2_control`. Move o robô por torque nas juntas, substitui completamente o `robot_sim.py` do antigo `amr_pallet`.
- [x] **SLAM real** — `slam_toolbox` `online_async` configurado em `src/rbot/mapping/rlai_mapping/`.
- [x] **EKF e AMCL configurados** — `robot_localization` (EKF) funde IMU + odom para `odom→base_footprint`; AMCL provê `map→odom`. Em `src/rbot/localization/rlai_localization/`.
- [x] **6 sensores**: LiDAR 2D, LiDAR 3D, IMU, câmera RGB-D, câmera estéreo, GPS — todos toggleáveis via launch args do `simulation.launch.py`.
- [x] **Nav2 estado-da-arte**: SMAC Hybrid-A* (planner global) + MPPI (controller local) + behavior tree + waypoint follower. Lifecycle todo `ACTIVE`. Goal `NavigateToPose` validado (SUCCEEDED).
- [x] **Build OK e robô rodando no Gazebo via VNC** — `colcon build` limpo; `ros2 launch rlai_bringup simulation.launch.py` + `rlai_navigation navigation.launch.py` sobe stack inteira; GUI no `DISPLAY=:1`.

### Falta fazer (portar do `amr_pallet` + adicionar)

- [ ] **Portar mundo galpão** — trazer `galp_amr.world` (pallets, doca, expedição) do antigo `amr_pallet` para `src/rbot/simulation/rlai_gazebo/worlds/`. Substitui ou complementa o `small_warehouse` atual. Gerar mapa 2D correspondente para AMCL.
- [ ] **Portar missão logística** — `logistics_mission` (state machine pickup → transit → drop) do antigo `amr_pallet`. Empacotar como nodo ROS 2 acima de `Nav2` (cliente das actions `/navigate_to_pose` e `/follow_waypoints`). Lugar provável: novo `src/rbot/missions/rlai_logistics/`.
- [ ] **Adicionar garfo elevador (junta `prismatic`)** — **não tem em `rbot`**, é trabalho nosso. Adicionar `fork_link` ligado ao `base_link` via joint prismatic em z, curso 0.0–0.20 m, controlador no `ros2_control`. Simular peso de pallet (até 500 kg) como link infantil que prende quando elevado (attach/detach plugin do Gazebo Harmonic).

**Implementado em 2026-05-18**: `galp_amr.sdf` foi portado para `rlai_gazebo`,
o mapa legado `galp_amr` foi empacotado em `rlai_mapping`, o pacote
`rlai_logistics` foi criado, e o garfo prismatico passou a subir/descer via
`fork_lift_controller`. Ainda falta validar a missao completa com Nav2, trocar
o mapa legado por um mapa SLAM gerado no mundo final e implementar attach/detach
do pallet.

**Critério de aceitação da fase**: rodar a stack, enviar missão "pegar pallet X e levar para doca Y", ver o robô navegar até o pallet com Nav2 real, parar embaixo, elevar o garfo, transportar até a doca, baixar, voltar.

---

## 4. Próximos passos (depois disso)

> **Foco**: chegar a uma missão completa pickup-deliver simulada.

- [ ] **AprilTag para docking de pallet** — câmera RGB no robô + marcador AprilTag colado no pallet. Pacote `apriltag_ros` (Jazzy). Posicionamento fino (±2 cm) antes de elevar o garfo. Validar precisão em simulação antes de hardware.
- [ ] **SLAM operacional** — `slam_toolbox` `online_async` já está configurado no `rbot` adotado; falta rodar contra o mundo Galp real e definir o fluxo de mapeamento inicial vs `lifelong` para operação.
- [ ] **Multi-robô (fleet básico)** — 2 ou 3 robôs num mesmo mundo Gazebo, namespaces ROS distintos (`/robot1/...`, `/robot2/...`). Coordenação simples (semáforo de zona/corredor). Antes de OpenRMF para entender o problema.
- [ ] **Modelar CAD no SolidWorks e importar** — desenhar chassi real, garfo, motorredutores, baterias. Exportar STL/STEP, gerar inércias do CAD, atualizar URDF com geometrias precisas. Saída: BOM mecânica para fabricação.

---

## 5. Backlog (ideias futuras)

> **Sem prazo.** Coletar agora, priorizar quando os Próximos Passos terminarem.

- [ ] **Interface web de controle** (referência `openamrobot/openamrobot-ui`) — dashboard React/Vue, visualização da frota, atribuição de missões, status em tempo real via rosbridge_websocket. Avaliar reuso direto do código `openamrobot-ui` clonado.
- [ ] **Integração com OpenRMF** (gestão de frota) — adapter dos nossos robôs ao Open-RMF da Open Robotics. Permite mistura com outros AMRs (interoperabilidade), porteiros automatizados, elevadores, etc. Trabalho grande, só faz sentido com 5+ robôs.
- [ ] **Detecção de pessoas (YOLO)** — câmera + YOLOv8 ONNX rodando no robô (Jetson Orin Nano ou equivalente). Usado **apenas** para parada de emergência se humano for detectado em zona robô-only — é o "fallback de segurança", não o modo de operação.
- [ ] **Modo "robô-only" formalizado (sem detecção de humanos)** — declaração de modo de operação no projeto: zonas demarcadas, política operacional ("nenhum humano além da entrada controlada"), sinalização (luz vermelha/sirene quando AMR ativo), bypass certificável de boa parte da norma ISO 3691-4. Diferencial comercial e técnico — reduz custo do robô em 30–50% vs AMR "human-aware".
- [ ] Carregamento autônomo (estação de docking + sensor de bateria + behavior tree de "low-battery → return to dock")
- [ ] Calibração intrínseca/extrínseca de sensores no campo (script + tutorial)
- [ ] Telemetria + logging (InfluxDB + Grafana ou Prometheus) — distância percorrida por robô, tempo por missão, falhas, ETA
- [ ] Integração WMS (REST/SOAP do cliente) — receber missão "pegar pallet 1234 do lote A e levar para doca 7"
- [ ] Hardening do hardware: PCB customizada, motorredutor sizing, encoder, battery management
- [ ] Certificação ABNT/INMETRO se aplicável

---

## 6. Decisões

> Registrar decisões importantes com data, contexto e responsável. ADR-style enxuto.

| # | Data | Decisão | Contexto / Justificativa | Status |
|---|---|---|---|---|
| 001 | 2026-05-13 | Adotar ROS 2 Jazzy + Gazebo Harmonic como stack alvo | Versões LTS, comunidade ativa, `setup_master.sh` automatiza | ✅ Vigente |
| 002 | 2026-05-13 | Foco "robô-only" como modo operacional principal | Reduz custo de safety/perception em 30-50%, viabiliza preço para PME brasileira | ✅ Vigente |
| 003 | 2026-05-14 | Adotar `rbot` como base e portar nossa missão por cima | Análise em `docs/RBOT_ANALYSIS.md` §7. Código importado para `src/rbot/` (Apache 2.0); build OK e sim rodando | ✅ Vigente |
| 004 | 2026-05-14 | Tração diferencial 2 rodas + 4 casters (herdada do `rbot`) | Consequência direta da Decisão #003; URDF já traz a topologia | ✅ Vigente |
| 005 | (pendente) | Carga máxima nominal (500 kg? 1000 kg? 1500 kg?) | Define tamanho do motor, bateria, chassi | 🟡 Em avaliação |
| 006 | (pendente) | CAD: SolidWorks vs FreeCAD vs Onshape | Ferramenta principal para modelagem mecânica | 🟡 Em avaliação |

---

## Convenções deste roadmap

- **Marque `[x]`** quando concluir, **mantenha o item** (vira histórico).
- **Promova** itens do Backlog para Próximos Passos quando começarem; de Próximos Passos para Atuais quando entrarem nas próximas 2 semanas.
- **Adicione decisões** na §6 sempre que escolher entre alternativas com impacto técnico ou de negócio.
- **Datas em ISO 8601** (`YYYY-MM-DD`) — sem ambiguidade Brasil/EUA.
- **Referencie outros docs** (ROBOT_ANALYSIS.md, RBOT_ANALYSIS.md, ARCHITECTURE.md, ONBOARDING.md) em vez de repetir conteúdo.
