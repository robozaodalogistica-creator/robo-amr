# Roadmap — AMR Pallet Galp

> **Documento vivo de planejamento.** Atualize sempre que decidir algo.
> Última atualização: 2026-05-13

---

## 1. Visão do produto

**AMR de pallet para galpão robô-only no Brasil, foco em PME.** Construímos um robô móvel autônomo de baixo custo para movimentação de pallets em galpões logísticos sem presença humana durante operação ("robô-only" — turnos noturnos, áreas restritas, dark warehouses). Mercado-alvo: pequenas e médias empresas brasileiras de logística e distribuição, que hoje não conseguem pagar AGV/AMR de fornecedores estrangeiros (Geek+, KION, Toyota) que custam US$ 50–150k por unidade. Diferenciais: stack 100% open source (ROS 2 Jazzy + Nav2), simulação realista antes de hardware, modo "robô-only" formalizado (dispensa toda a complexidade e custo de detecção/segurança humana).

---

## 2. Estado atual

**O que funciona hoje** (ver `docs/ROBOT_ANALYSIS.md` para detalhes do `amr_pallet` e `docs/RBOT_ANALYSIS.md` para o `rbot`):

| Componente | Status atual | Observação |
|---|---|---|
| Workspace ROS 2 Jazzy | ✅ Instalado e funcionando | `setup_master.sh` reinstala em ~10 min |
| Gazebo Harmonic | ✅ Rodando com VNC streaming | `start_gui.sh`, `start_amr_gui.sh` |
| `amr_pallet` (protótipo atual) | 🟡 Anda no galpão fake, sem física real | URDF cosmético, LiDAR fake (todos `inf`), `robot_sim.py` integra `cmd_vel` por dead reckoning |
| Nav2 (planner DWB básico) | 🟡 Funciona com `LaserScan` fake | Sem obstacle avoidance real porque LiDAR não enxerga nada |
| Mapa do galpão | 🟡 `galp_amr.yaml` placeholder | Sem mundo Galp real modelado |
| `rbot` clonado | ✅ Stack alternativa avaliada | URDF real, MPPI+SMAC, EKF+AMCL, SLAM Toolbox — não integrado ainda |
| Documentação | ✅ ARCHITECTURE.md, ONBOARDING.md, ROBOT_ANALYSIS.md, RBOT_ANALYSIS.md, README.md no repo |

**Limitações que travam o produto** (ordenadas por impacto):
1. Sem física real → impossível validar tração, escorregamento, dinâmica
2. LiDAR fake → impossível validar Nav2 com obstáculos
3. Sem mecanismo de elevação → não é uma empilhadeira, é só um carrinho
4. Sem mundo Galp modelado → testes não representam realidade
5. Falta lógica de docking de pallet (AprilTag/visão)

---

## 3. Objetivos atuais (próximas 2 semanas)

> **Foco**: sair do "robô fake" para um robô que **simula como um robô de verdade**.

- [x] **Avaliar se partimos do `rbot` ou continuamos com `amr_pallet`** — **CONCLUÍDO: adotamos `rbot` como base.** Código importado para `src/rbot/` (Apache 2.0, ver `NOTICE.md` e `THIRD_PARTY_LICENSES.md`). A partir de agora modificamos livremente para o caso de uso AMR-de-pallet em galpão robô-only; portamos nossa lógica de missão por cima do esqueleto do rbot.
- [ ] **Construir URDF real do robô com física** — massa, tensores de inércia, joints `continuous` para rodas, `fixed` para sensores. Se for adoção de `rbot`, já temos pronto. Se mantermos `amr_pallet`, é trabalho do zero.
- [ ] **LiDAR funcionando** — raycast real do Gazebo (`gpu_lidar` plugin), 360° / 720 raios / σ ≈ 0.01 m. Substituir o `LaserScan` fake do `robot_sim.py`.
- [ ] **Plugin diff-drive (substituir `robot_sim.py`)** — usar `gz_ros2_control` + `diff_drive_controller` do `ros2_control`. Move o robô por torque nas juntas, não por teleporte.
- [ ] **Mecanismo de elevação (junta `prismatic`)** — adicionar garfo ao URDF: link `fork_link` ligado ao `base_link` via joint prismatic em z, curso 0.0–0.20 m, controlador `position_controllers/JointPositionController`. Simular peso de pallet (até 500 kg) como link infantil que prende quando elevado.

**Critério de aceitação da fase**: rodar `ros2 launch ... simulation.launch.py`, dar `Nav2 Goal` no RViz, ver o robô andar por torque real, desviar de obstáculos vistos pelo LiDAR, parar embaixo de um pallet, elevar o garfo, e arrastar o pallet.

---

## 4. Próximos passos (depois disso)

> **Foco**: chegar a uma missão completa pickup-deliver simulada.

- [ ] **AprilTag para docking de pallet** — câmera RGB no robô + marcador AprilTag colado no pallet. Pacote `apriltag_ros` (Jazzy). Posicionamento fino (±2 cm) antes de elevar o garfo. Validar precisão em simulação antes de hardware.
- [ ] **SLAM real (`slam_toolbox`)** — substituir mapa estático por SLAM online. Modo `online_async` para mapeamento inicial, `lifelong` para operação. Já configurado no `rbot`.
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
| 003 | (pendente) | Adotar `rbot` como base ou continuar com `amr_pallet` | Análise em `docs/RBOT_ANALYSIS.md` §7 recomenda híbrido (rbot + portar nossa missão) | 🟡 Em avaliação |
| 004 | (pendente) | Tração diferencial (2 rodas + 4 casters) ou outra topologia | `rbot` usa diff-drive 2+4 — provavelmente herdamos | 🟡 Em avaliação |
| 005 | (pendente) | Carga máxima nominal (500 kg? 1000 kg? 1500 kg?) | Define tamanho do motor, bateria, chassi | 🟡 Em avaliação |
| 006 | (pendente) | CAD: SolidWorks vs FreeCAD vs Onshape | Ferramenta principal para modelagem mecânica | 🟡 Em avaliação |

---

## Convenções deste roadmap

- **Marque `[x]`** quando concluir, **mantenha o item** (vira histórico).
- **Promova** itens do Backlog para Próximos Passos quando começarem; de Próximos Passos para Atuais quando entrarem nas próximas 2 semanas.
- **Adicione decisões** na §6 sempre que escolher entre alternativas com impacto técnico ou de negócio.
- **Datas em ISO 8601** (`YYYY-MM-DD`) — sem ambiguidade Brasil/EUA.
- **Referencie outros docs** (ROBOT_ANALYSIS.md, RBOT_ANALYSIS.md, ARCHITECTURE.md, ONBOARDING.md) em vez de repetir conteúdo.
