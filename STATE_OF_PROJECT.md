# 📌 Estado do Projeto AMR

> **Documento de continuidade** — quando começar nova conversa com Claude,
> primeiro pedido é: "leia STATE_OF_PROJECT.md no meu repo robo-amr e me
> coloque a par do projeto antes de seguirmos".
> 
> Atualizado periodicamente para manter contexto entre conversas.
>
> Última atualização: 2026-05-24

---

## 👤 Sobre mim (France)

- Engenheiro mecânico brasileiro
- Já construí curvadora industrial estilo Huth (530kg, hidráulica)
- Não programo — uso Claude Code + Claude Web como colaborador
- Sócio: Pedro Barazetti (pbarazetti no GitHub), programador
- Orçamento limitado, cloud-only por enquanto
- Trabalho com paciência, foco em validação antes de gastar

---

## 🎯 Visão do produto

**AMR de pallet para galpão robô-only no Brasil**, focado em PMEs.

Diferencial estratégico: galpão sem humanos elimina certificação ISO 3691-4,
reduz custo 40-60% versus AMR tradicional. Meta de US$ 50-80k/unidade vs
US$ 150k de Toyota/KION/Geek+.

Mercado-alvo: 3PL, distribuidores, regional e-commerce brasileiros.

---

## 🛠️ Stack técnica

| Camada | Tecnologia |
|---|---|
| OS | Ubuntu 24.04 |
| Framework | ROS 2 Jazzy |
| Simulador | Gazebo Harmonic |
| Navegação | Nav2 (SMAC + MPPI) |
| SLAM | SLAM Toolbox |
| Localização | EKF + AMCL |
| Controle | ros2_control + diff-drive |
| Visualização | Foxglove + VNC via cloudflared |
| Robô base adotado | **rbot** (Black Coffee Robotics, Apache 2.0) |
| CAD futuro | Fusion 360 (grátis para uso pessoal) |
| Cloud | RunPod (RTX A5000) |
| Repo | https://github.com/robozaodalogistica-creator/robo-amr |

---

## ✅ O que funciona hoje

- Setup_master.sh idempotente reinstala tudo em 10 min
- Robô rbot rodando em Gazebo com física real
- Navegação autônoma validada (NavigateToPose com SUCCEEDED)
- Mundo `galp_amr.sdf` portado para Gazebo Harmonic com pallets, doca e expedição
- Garfo elevador simulado (`fork_lift_joint`) sobe/desce via `fork_lift_controller`
- Missão `rlai_logistics` criada: carrega waypoints por YAML e sequencia Nav2 + garfo
- Smoke test Phase 1 validou a missão completa: 4 pallets entregues, garfo subindo/baixando, e retorno para home
- Infraestrutura Gazebo attach/detach criada no caminho opt-in: `galp_amr_attach`, pallets dinâmicos, `detachable_pallets_enabled:=true`, `DetachableJoint` e tópicos ROS `/pallet_N/attach` e `/pallet_N/detach`
- Pipeline SLAM headless do `galp_amr` validado em 2026-05-23; candidatos foram salvos em `/tmp`, mas o mapa rastreado ainda nao foi substituido porque o LiDAR 2D passa acima dos pallets baixos e o candidato ficou mais ruidoso que o mapa legado
- Pacote `rlai_apriltag` criado em `src/rbot/perception/rlai_apriltag/`: launch/config para `apriltag_ros` com tags 36h11 dos 4 pallets; dependencia ROS instalada, texturas reais geradas em `rlai_gazebo/models/pallet_tags` e boards adicionados nos mundos `galp_amr`/`galp_amr_attach`; smoke test runtime validado em 2026-05-24 com deteccao de `tag36h11 id=1`, `hamming=0`, decision margin ~235
- 6 sensores funcionais (LiDAR 2D, 3D, IMU, RGB-D, estéreo, GPS)
- Modo didático com control_panel.py (pausa/play/velocidade)
- Visualização VNC via cloudflared
- Documentação técnica completa
- GitHub sincronizado até o último commit; mudanças SLAM/AprilTag desta sessão ainda locais até stage/commit/push

---

## 🟡 Estado atual da Fase 1

Em 2026-05-19, a Phase 1 fechou em simulação headless:
`MISSION_SUCCESS delivered=4/4 t=576.8s`. Depois da trilha opt-in de
attach/detach, a missão padrão foi revalidada no `galp_amr` estático com
`MISSION_SUCCESS delivered=4/4 t=571.5s`. A missão validada sequencia Nav2 +
garfo para quatro ciclos pickup → entrega e retorna para `home`.

Observação importante: `expedicao` e `doca` estão como staging poses
navegáveis, não como docagem física final. Isso evita regiões infladas/ocupadas
do mapa legado enquanto AprilTag docking e attach/detach ainda não existem.

Também em 2026-05-19, o attach/detach físico foi preparado no Gazebo em um
caminho opt-in (`world:=galp_amr_attach` +
`detachable_pallets_enabled:=true`) e validado com comando direto
(`attached`/`detached` em `/pallet_1/attach_state`). Ele não fica ligado no
fluxo padrão da missão porque os waypoints atuais ainda não colocam o garfo
embaixo do pallet.

---

## 🚧 O que falta fazer

### Próximas fases técnicas

- Manter o mapa legado por enquanto; o SLAM novo do `galp_amr` foi reproduzido, mas o LiDAR 2D passa acima dos pallets baixos e o candidato ficou mais ruidoso
- Substituir staging poses por docking real com aproximação fina
- Integrar `world:=galp_amr_attach`, `detachable_pallets_enabled:=true` e `enable_gazebo_attach:=true` depois que o docking real estiver validado
- 🎯 AprilTag docking (±2cm precisão): próximo passo é transformar `/apriltag/detections` em comando de aproximação fina antes de ligar attach/detach na missão
- 🤖 Multi-robô (fleet básico)
- 🛠️ Hardware físico (fase futura)

### Decisões pendentes

- Vertical de mercado (e-commerce, farmacêutico, frigorífico?)
- Capacidade do robô (200kg, 500kg, 1ton?)
- Modelo de negócio (venda vs RaaS aluguel?)

---

## 📚 Documentação no repo (importante ler)

| Documento | Função |
|---|---|
| README.md | Visão geral + estado |
| ROADMAP.md | Próximos objetivos |
| docs/RBOT_ANALYSIS.md | Análise do robô adotado |
| docs/CODE_GUIDE.md | Onde mexer no código |
| docs/HARDWARE_ANATOMY.md | Anatomia técnica do robô |
| docs/COMO_O_ROBO_ANDA_1_METRO.md | Passo a passo detalhado |
| docs/SLAM_GALP_MAPPING.md | Nota do experimento SLAM no mundo Galp |
| docs/ESTUDO_DIDATICO.md | Caderno de estudo (vivo) |
| docs/O_QUE_PRECISO_ALTERAR.md | Guia prático para meu robô |

---

## 💡 Decisões importantes já tomadas

### Adoção do rbot (15/05/2026)
Em vez de continuar amr_pallet do zero, adotamos rbot como base.
Pulamos ~4 meses de desenvolvimento. rbot tem URDF, física, sensores,
Nav2 SMAC+MPPI, SLAM, AMCL, EKF — tudo profissional.

### RunPod como infraestrutura cloud
Network Volume "Robotica" garante persistência de dados.
Setup_master.sh resolve reset do Container Disk em 10 min.
Pod com RTX A5000 a US$ 0.28/h.

### Claude Code Remote Control
Sessões longas funcionam via claude.ai/code, resistente a quedas
de conexão. Web Terminal do RunPod só para emergências.

### Fusion 360 para CAD
Versão grátis Personal Use (3 anos) para projeto pessoal.
Compatível com PC i5-4460 + 16GB + RX 580.
Migrar para SolidWorks quando virar empresa.

---

## 🧠 Conceitos técnicos já estudados

- Os 3 loops do robô (Planejador 1Hz, Controlador 20Hz, Executor 100Hz)
- Behavior Tree (substituto de PLC em robôs)
- SMAC Hybrid-A* (algoritmo de planejamento)
- Open List / Closed List (estrutura de busca)
- MPPI controller (simula 2000 trajetórias futuras)
- ROS 2 como framework (idioma comum)
- Diferença entre framework, software e driver
- SLAM (Simultaneous Localization and Mapping)
- Análogos industriais (CLP ↔ ROS, drives ↔ ros2_control, etc)

---

## 🛣️ Roadmap pessoal de aprendizado

Em estudo agora:
- [x] Bloco 1: Os 3 loops do robô
- [x] Bloco 2: Loop 1 (Planejador) - BT + SMAC
- [x] Bloco 3: Parâmetros vs Algoritmos
- [x] Bloco 4: Especificações rbot
- [x] Bloco 5: SLAM conceito
- [x] Bloco 6: Loop 2 (MPPI Controller)
- [ ] Bloco 7: Loop 3 (Executor + ros2_control)
- [ ] Bloco 8: Sensores e Localização (AMCL + EKF)
- [ ] Bloco 9: Como LiDAR vira costmap
- [ ] Bloco 10: SLAM matemática básica
- [ ] Bloco 11: Como adaptar para meu robô físico

---

## 💰 Estado financeiro do projeto

- Investimento atual: ~US$ 30 em RunPod
- Tempo investido: ~5 dias de trabalho
- Receita: zero (fase de validação)
- Próximo gasto: nenhum imediato (continua na simulação)

---

## 🚦 Onde estamos no roadmap macro

---

## ⚠️ Restrições e cuidados aprendidos

- Nunca vazar tokens GitHub em conversas (já vazei 2)
- Sempre revogar tokens depois de uso
- Stop pod no RunPod ao final do dia (não Terminate)
- Network Volume é separado de Container Disk
- Editar pod reseta Container Disk
- Web Terminal cai com frequência, usar Remote Control

---

## 📞 Contato para continuidade

- GitHub: robozaodalogistica-creator
- Email: robozaodalogistica@gmail.com
- Repo principal: https://github.com/robozaodalogistica-creator/robo-amr

---

## 🤖 Instrução para Claude em conversa nova

Quando France iniciar nova conversa, leia este documento primeiro.
Após ler, pergunte: "Em qual ponto do roadmap quer continuar?"
Não recomeçar do zero — usar o contexto acumulado.

Adapte a profundidade técnica ao nível do France:
- Engenheiro mecânico, não programador
- Aprende por blocos digestíveis com analogias industriais
- Prefere "decida você como me explicar" a múltipla escolha
- Quer respostas diretas, sem rodeios
- Aprecia honestidade sobre limitações (técnicas e de mercado)
