# 📚 Caderno de Estudo do AMR

> Documento vivo onde France registra o aprendizado conceitual sobre o robô.
> Estilo: didático, com analogias industriais (CLP, CNC, drives, encoders).
> Atualizado conforme estudo cada bloco.

---

## 🎯 Bloco 1: A grande sacada — Os 3 loops do robô

O robô tem **3 loops rodando ao mesmo tempo**, em frequências diferentes.
Cada um faz uma coisa específica.

### Analogia: gerência de obra civil

| Nível | Frequência | Quem faz | O que decide |
|---|---|---|---|
| Engenheiro mestre | 1x/hora | bt_navigator + planner | "Estamos atrasados? Replanejar?" |
| Mestre de obras | 1x/min | controller (MPPI) | "Qual a próxima tarefa?" |
| Operário | 1x/seg | diff_drive + Gazebo | "Levanta tijolo, coloca argamassa..." |

### Aplicado ao robô

| Loop | Frequência | Quem | Pergunta que responde |
|---|---|---|---|
| **Planejador** | **1 Hz** | bt_navigator + planner_server | "Por onde devo ir?" |
| **Controlador** | **20 Hz** | controller_server (MPPI) | "Que velocidade mando agora?" |
| **Executor** | **100 Hz** | diff_drive_controller + Gazebo | "Quanto cada motor gira?" |

### Por que 3 loops e não 1

- Planejador é **caro** (calcula caminho) — não precisa rodar 100x/seg
- Executor é **rápido** (PID do motor) — precisa ser ágil
- Controlador é **intermediário** — faz a ponte

**Sensores rodam em paralelo** alimentando todos os loops.

---

## 🗺️ Bloco 2: Loop 1 — O Planejador (1 Hz)

Esse loop responde: "**Por onde devo ir?**"

### Componente 1: Behavior Tree (`/bt_navigator`)

É o **cérebro decisor**. Análogo ao PLC mestre de uma fábrica.

| CLP industrial | Behavior Tree |
|---|---|
| Ladder logic | XML com nós |
| Sequencial | Hierárquica |
| If/then/else | Sequence/Selector |
| Retry block | RecoveryNode |

A BT do nosso robô:

**Observação**: roda 10x/seg, mas só replaneja 1x/seg (RateController).

### Componente 2: SMAC Hybrid-A* (`/planner_server`)

O **algoritmo que desenha o caminho**.

**A\* básico**: trata o mapa como tabuleiro de xadrez. Para cada casa:
- `g(casa)` = custo já gasto até aqui
- `h(casa)` = estimativa do custo restante até o goal
- `f = g + h` (sempre expande o menor f → caminho ótimo)

**Hybrid-A\***: adiciona curvas suaves (Dubin) respeitando raio mínimo de viragem.

**Parâmetro chave**: `minimum_turning_radius: 0.25m` — depende do tipo do robô.

### Open List vs Closed List

| Lista | Função |
|---|---|
| **Open List** | Casas descobertas mas não exploradas |
| **Closed List** | Casas já exploradas (não volta) |

**Por que precisa das 2?**
- Sem Closed List → loop infinito (volta no mesmo lugar)
- Sem Open List → não sabe próximo passo

**Termina quando**:
- Achou o goal ✅
- Open list vazia (sem caminho)
- Timeout 5s

### Analogia industrial

| Mundo industrial | Algoritmo |
|---|---|
| Ordens em fila no MES | Open List |
| Ordens já produzidas | Closed List |
| Selecionar ordem urgente | Tirar de Open (menor f) |

---

## ⚙️ Bloco 3: Parâmetros vs Algoritmos

**Pergunta crítica**: Se mudar o robô, preciso reescrever tudo?

**Resposta**: NÃO. Algoritmos ficam. Parâmetros mudam.

### O que NÃO muda (universal)

- Código do A*/Hybrid-A*
- Algoritmo MPPI
- EKF, AMCL
- Estrutura Open/Closed List

Esses são **milhões de linhas** que ninguém reescreve.

### O que VOCÊ ajusta (parâmetros)

**Arquivos YAML** onde mora 80% do trabalho de customização:

- `nav2_params.yaml` — parâmetros de navegação
- `controllers.yaml` — limites do motor
- `velocity_smoother.yaml` — rampa de aceleração
- `ekf.yaml` — fusão sensorial
- `amcl.yaml` — localização

Parâmetros típicos que mudam:

```yaml

### 2 modos

**Online (em tempo real)**: robô constrói mapa enquanto navega
- AMR em galpão novo
- Drone explorando área desconhecida

**Offline (pós-processamento)**: grava tudo, depois reconstrói
- Mochilas de mapeamento (Leica, NavVis)
- Drones topográficos

### Tipos de SLAM

| Tipo | Sensor principal | Aplicação |
|---|---|---|
| Visual SLAM | Câmera | Drone, AR/VR |
| LiDAR SLAM 2D | LiDAR 2D | AMR indoor |
| LiDAR SLAM 3D | LiDAR 3D | Carro autônomo |
| LiDAR-Inertial SLAM | LiDAR + IMU | Robô premium |

**No nosso rbot**: SLAM Toolbox (LiDAR 2D SLAM).

### Loop closure (a mágica)

Quando o robô passa em lugar que já passou, SLAM **reconhece** e corrige o mapa retroativamente. Isso elimina drift acumulado.

---

## 🎮 Bloco 7: Loop 2 — O Controlador MPPI (20 Hz)

Esse loop responde: "**Estou andando esse caminho. Que velocidade mando AGORA?**"

### MPPI = Model Predictive Path Integral

**A grande sacada**: simula **2000 futuros possíveis** e escolhe o melhor.

### Como funciona (a cada 50ms)

**Passo 1** — Gera 2000 trajetórias candidatas
Cada uma com 56 passos no futuro (~2.8 segundos de horizonte).
Cada uma com velocidades aleatórias diferentes.

**Passo 2** — Avalia cada trajetória usando 8 critérios

| Critério | Pune quando... |
|---|---|
| PathFollow | Sai do caminho planejado |
| PathAngle | Vira diferente do caminho |
| Obstacles | Passa perto demais de obstáculo |
| PreferForward | Anda de ré sem precisar |
| Goal | Anda longe do objetivo |
| GoalAngle | Fica de costas para o goal |
| Velocity | Oscila velocidade |
| CostmapInflation | Entra em zona perigosa |

**Passo 3** — Escolhe a melhor trajetória (menor custo total)

**Passo 4** — Executa apenas o primeiro passo
Pega só o primeiro comando da trajetória vencedora.

**Passo 5** — 50ms depois, repete tudo do zero

### Por que simular 2000 futuros em vez de calcular direto

**Não dá para calcular direto** porque:

1. Mundo é não-linear (motor satura, derrapa, terreno inclina)
2. Restrições mudam o tempo todo (obstáculos aparecem)
3. Trade-offs múltiplos (rápido vs suave vs seguro)

**Não existe fórmula fechada**. Simular é a forma viável.

### Por que 2000 trajetórias

| Trajetórias | Qualidade | CPU |
|---|---|---|
| 100 | Ruim | Baixíssima |
| 500 | Médio | Baixa |
| 2000 | Bom | Média (sweet spot rbot) |
| 10000 | Ótimo | Alta |

### Por que 56 passos (2.8s no futuro)

- Curto demais (0.5s): reage tarde
- Longo demais (10s): mundo muda muito, predições viram inúteis
- 2.8s: equilibrado

### Analogia com motorista humano

Você dirigindo:
- Olha 30-50m à frente (não 5m, nem 500m)
- Imagina mentalmente 3-4 trajetórias possíveis
- Escolhe a melhor e executa um pedacinho
- Reavalia constantemente

**MPPI faz a mesma coisa matematicamente** em vez de intuitivamente.

### Hardware envolvido

**Não é hardware, é algoritmo.** Roda na CPU do robô (Pi 5 ou similar).

### Parâmetros principais (no Pi 5)

| Parâmetro | rbot (cloud) | Pi 5 estimado |
|---|---|---|
| batch_size | 2000 | 800-1500 |
| time_steps | 56 | 40-50 |
| controller_frequency | 20 Hz | 15-20 Hz |

---

## 🔗 Bloco 8: ROS 2 como Framework

### Framework vs Software

| | Framework | Software |
|---|---|---|
| Exemplo | ROS 2 | Nav2, SLAM Toolbox |
| Função | Infraestrutura comum | Resolve problema específico |
| Analogia | Shopping inteiro | Lojas dentro do shopping |

### Por que ROS 2 é revolucionário

Antes do ROS (2007): cada laboratório tinha framework próprio, código não compartilhável.

Depois do ROS: comunidade global compartilha código, inovação acelerou 10x.

### O que ROS 2 fornece

**1. Tipos de mensagem padronizados**
- LaserScan = formato padrão para LiDAR
- Image = formato padrão para câmera
- Twist = formato padrão para velocidade

**2. Sistema de transporte de mensagens (DDS)**
Entrega mensagens entre processos sem você programar TCP/IP.

**3. Descoberta automática**
Processos se descobrem entre si na rede.

### Pacotes que usam ROS 2

- Nav2 (navegação)
- MoveIt (manipuladores)
- SLAM Toolbox (mapeamento)
- ros2_control (controle motor)
- Foxglove Bridge (visualização)
- Centenas de outros

**Todos conversam entre si** porque seguem o padrão ROS 2.

### Drivers — específicos do hardware

Cada componente físico tem **driver** próprio que conecta com o ROS 2:

| Componente | Driver | Tópico publicado |
|---|---|---|
| RPLiDAR A2 | sllidar_ros2 | /scan |
| Câmera Pi v2 | raspicam2 | /image_raw |
| Motor com encoder | ros2_control + hw interface | /joint_states |

**Software (Nav2, SLAM) é genérico. Driver é específico.**

---

## 📌 Próximos blocos a estudar

- [x] Bloco 1: Os 3 loops do robô
- [x] Bloco 2: Loop 1 (Planejador) — BT + SMAC
- [x] Bloco 3: Parâmetros vs Algoritmos
- [x] Bloco 4: Como ajustar parâmetros
- [x] Bloco 5: Especificações do rbot
- [x] Bloco 6: SLAM (conceito)
- [x] Bloco 7: Loop 2 (MPPI Controller)
- [x] Bloco 8: ROS 2 como Framework
- [ ] **Bloco 9: Loop 3 — Executor + ros2_control**
- [ ] Bloco 10: Sensores e Localização (AMCL + EKF)
- [ ] Bloco 11: Como o LiDAR vira costmap (percepção)
- [ ] Bloco 12: SLAM matemática básica
- [ ] Bloco 13: Como adaptar para meu robô físico

---

## 💡 Conceitos-chave aprendidos

### Mapa mental do robô
### Insights importantes

1. **Algoritmos são universais, parâmetros são meus**
2. **Iteração beats cálculo** (engenheiro testa, mede, ajusta)
3. **Não precisa reinventar a roda** (Nav2 + rbot resolvem 80%)
4. **80% do trabalho está nos YAMLs**, não em código novo
5. **URDF é o equivalente ROS do CAD** do robô
6. **MPPI simula porque calcular direto é impossível**
7. **ROS 2 é o idioma comum** que une centenas de softwares
8. **Driver é específico, software é genérico**
9. **Loop closure** elimina drift acumulado no SLAM
10. **Framework não faz nada sozinho**, é infraestrutura
