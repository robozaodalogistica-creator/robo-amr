# 📚 Caderno de Estudo do AMR

> Documento vivo onde France registra o aprendizado conceitual sobre o robô.
> Estilo: didático, com analogias industriais (CLP, CNC, drives, encoders).
> Atualizado conforme estudo cada bloco.

---

## 🎯 Bloco 1: Os 3 loops do robô (versão profunda)

> Atualizado: 19/05/2026 — substitui versão inicial superficial.
> Estilo: mecanismo + porquê + analogia industrial + pergunta de verificação.

### Por que loops e não uma função sequencial

Máquina industrial simples tem código linear: "se sensor X ativou, liga motor Y, espera Z segundos, desliga". Sequencial.

Robô móvel não pode ser assim. Em paralelo, o robô precisa:
- Ler LiDAR (15 Hz no rbot)
- Ler IMU (200 Hz)
- Ler encoders das rodas (100 Hz)
- Decidir para onde ir (~1 Hz)
- Ajustar velocidade comandada (~20 Hz)
- Controlar rotação de cada motor (100 Hz)

Se tudo isso fosse sequencial, cada ciclo gastaria a SOMA de todas as tarefas. O robô reagiria devagar — como motorista que termina de olhar a estrada antes de começar a virar o volante. Bate.

A solução é paralelismo. Mas paralelismo bagunçado é pior que sequencial. A comunidade de robótica descobriu que as decisões se organizam em 3 níveis de abstração, cada um com frequência natural diferente.

### Os 3 níveis de decisão

| Nível | Pergunta | Frequência típica | Algoritmo no rbot |
|---|---|---|---|
| Estratégico | "Por onde devo ir?" | 1 Hz | SMAC Hybrid-A* (planner_server) |
| Tático | "Que velocidade mando AGORA?" | 20 Hz | MPPI (controller_server) |
| Baixo nível | "Quanto cada motor gira?" | 100 Hz | PID dentro do diff_drive_controller |

### Por que cada frequência (mecanismo, não arbitrária)

**Planejador a 1 Hz — DOIS motivos juntos:**

1. **Mapa muda devagar.** Caminho até a doca não precisa ser recalculado 100x/seg.
2. **Cálculo é caro.** A* expande células do grafo uma a uma, mantém open list e closed list, calcula custos. Para mapa de 400×400 células, leva dezenas a centenas de ms. Rodar a 100 Hz seria impossível — CPU não termina uma busca antes da próxima começar.

**Controlador a 20 Hz — equilíbrio entre reatividade e custo:**

- Tem que reagir a obstáculos dinâmicos (pessoa cruzando, pallet fora do lugar). Lento demais = colisão.
- MPPI simula 2000 trajetórias por ciclo. Custa CPU. Rodar a 100 Hz seria caro demais.
- 20 Hz (a cada 50 ms) é o sweet spot.

**Executor a 100 Hz — física do motor:**

- Motor responde rápido. Se você atrasa a correção, o motor "passa do ponto" — queria 0.5 m/s, quando o controle percebe já está em 0.7, corrige demais e cai para 0.3. Oscilação clássica.
- Regra de teoria de controle: frequência de controle ≥ 10× a dinâmica do sistema controlado. Motor responde em ~50 ms → controle a 100 Hz (10 ms entre correções) é seguro.

### Como os loops se conversam

Cada loop produz saída que vira entrada do loop abaixo:

```
Loop Planejador (1 Hz)
  ↓ produz: caminho (lista de pontos x,y até o goal)
Loop Controlador (20 Hz)
  ↓ produz: velocidade comandada (vx linear, ωz angular)
Loop Executor (100 Hz)
  ↓ produz: rotação de cada motor (ω_esquerda, ω_direita)
Mundo físico (motor, roda, chão)
  ↓ produz: movimento real, encoders, IMU
  ↑ feedback retorna para todos os loops acima
```

Cada loop NÃO espera o loop de cima. Controlador trabalha com último caminho disponível (mesmo que de 0.9s atrás). Executor trabalha com última velocidade comandada. Isso permite paralelismo real.

### Por que separar em 3 e não fazer 1 algoritmo gigante

Separação de responsabilidades. Cada loop é um TIPO diferente de problema matemático:

- **Planejador** = busca em grafo (otimização discreta). Algoritmos: A*, Dijkstra, RRT. Não precisa de física, só de mapa.
- **Controlador** = otimização contínua sob restrições (física + obstáculos). Algoritmos: MPC, MPPI, DWA. Precisa de dinâmica.
- **Executor** = controle clássico (fechar malha de velocidade no motor). Algoritmo: PID. Precisa do motor.

Juntar tudo num algoritmo só = monstro gigante, lento, impossível de debugar. Separado = cada parte testada, ajustada, substituída independentemente.

### Por que isso importa para diagnóstico (aplicação prática)

Saber em qual loop está o problema é metade do trabalho de debug. Padrões:

| Sintoma | Loop provável | O que ajustar |
|---|---|---|
| Robô anda em círculos sem chegar no goal | Planejador (1) | Raio mínimo de viragem, custo de marcha-ré no A* |
| Robô bate em obstáculo que apareceu de repente | Controlador (2) | Peso do critério "Obstacles" no MPPI |
| Robô vibra/trepida ao acelerar | Executor (3) | PID do motor, rampa do velocity_smoother |
| Robô segue caminho em zigue-zague suave (serpenteia) | Controlador (2) | Peso do critério "PathAlign" no MPPI |

Regra prática para descobrir o loop: **em qual escala de tempo o problema acontece?**
- Milissegundos (trepidação) → Loop 3 (rápido)
- Décimos de segundo (zigue-zague) → Loop 2 (médio)
- Segundos (rota errada) → Loop 1 (lento)

### Analogia industrial (para o engenheiro mecânico)

| Mundo industrial | Robô |
|---|---|
| Planejamento de produção (ERP/MES, decide ordem do dia) | Loop 1 — Planejador (1 Hz) |
| Supervisório SCADA (decide setpoints a cada minuto) | Loop 2 — Controlador (20 Hz) |
| Drive servo do motor (fecha malha de velocidade) | Loop 3 — Executor (100 Hz) |
| Sensor de campo (encoder, IMU, LiDAR) | Sensores em paralelo |

CLP industrial moderno funciona com mesma hierarquia: laços rápidos (PID de motor) embaixo, lógica de sequenciamento no meio, decisão estratégica em cima. A novidade do robô é que o "supervisório" (Loop 2) é MPPI, não ladder logic.

### Perguntas de verificação

Responda sem olhar o material acima.

1. Por que o Planejador roda a 1 Hz e não a 100 Hz? (DOIS motivos)
2. Por que o Executor precisa rodar a 100 Hz e não a 1 Hz? (motivo de física, não de obstáculos)
3. Robô oscila ao acelerar (alta frequência, milissegundos): qual loop?
4. Robô serpenteia ao seguir reta (baixa frequência, segundos): qual loop?
5. Qual loop é responsável por desviar de obstáculo dinâmico?

Respostas corretas:
1. (a) Mapa muda devagar (b) Cálculo é caro — A* não termina busca em <10ms
2. Motor é físico, atraso na correção causa oscilação (regra: controle ≥10× dinâmica do sistema)
3. Loop 3 (Executor) — PID mal sintonizado ou rampa agressiva
4. Loop 2 (Controlador) — peso PathAlign do MPPI baixo
5. Loop 2 (Controlador). Loop 3 não enxerga obstáculos.

---

## Bloco 2: Loop 1 — O Planejador (1 Hz)

Atualizado: 20/05/2026 — versão profunda, substitui versão superficial inicial. Esta atualização cobre o Componente 1 (Behavior Tree). O Componente 2 (A*) será adicionado a seguir.

### Por que o Loop 1 tem DOIS componentes ROS e não um só

O Loop 1 não é "um algoritmo só". São duas peças trabalhando em conjunto:

Componente Behavior Tree no nó ROS /bt_navigator responde "O que devo fazer agora? Continuar, replanejar, dar ré, esperar, abortar?". Análogo industrial: PLC mestre rodando ladder/SFC.

Componente Planejador A* no nó ROS /planner_server responde "Dado o objetivo, qual o melhor caminho geométrico?". Análogo industrial: Software CAM gerando trajetória CNC.

A separação existe porque são tipos diferentes de problema. BT resolve LÓGICA de decisão (sequência, alternativas, recovery, retry). A* resolve GEOMETRIA de caminho (busca em grafo, primitivas Dubin, obstáculos). Quando o robô precisa decidir "devo tentar replanejar ou já desisto?", isso é BT. Quando precisa decidir "qual o melhor caminho dessa pose até essa outra?", isso é A*. Juntar tudo num só algoritmo seria monstruoso.

### Dois significados de "nó" — esclarecimento importante

A palavra "nó" é usada em DUAS camadas diferentes do ROS/Nav2.

Nó ROS 2 é um processo do sistema operacional. Aparece em ros2 node list. Vive no OS / rede ROS.

Nó de Behavior Tree é um elemento dentro do XML da árvore. Sequence, Selector, RateController, etc. Vive dentro do XML, na memória do bt_navigator.

O bt_navigator é UM nó ROS 2. Dentro dele, na memória, existe uma ÁRVORE de nós BT. Esses nós BT não são processos — são estruturas de dados.

Verificação: rode ros2 node list durante uma navegação. Você verá bt_navigator, planner_server, controller_server, behavior_server como processos separados. Não verá "Sequence" ou "RateController" — esses são internos.

### Componente 1: Behavior Tree (/bt_navigator)

#### O problema que ela resolve

No mundo real, mil coisas dão errado: caminho bloqueado, pallet fora do lugar, bateria baixa, pessoa na frente, robô se perde, missão cancelada.

Você precisa de uma estrutura de decisão capaz de tentar caminho A; se falhar, tentar B; se falhar, recuperação; se falhar, desistir. Também precisa estrangular taxa de execução de operações caras (não pode replanejar 100x/s). E lembrar onde parou entre ticks (FollowPath durou 5 segundos, precisa retomar).

Tentativas alternativas falham. Código sequencial vira pirâmide de if-else. Máquina de estados em sistemas grandes vira "espaguete" de transições. BT é a solução adotada pela comunidade de robótica.

#### Como funciona a avaliação

A árvore é ticada 10 vezes por segundo. Cada tick começa na raiz, desce pela árvore em série (esquerda para direita), e cada nó retorna um de três estados.

SUCCESS significa que esse nó terminou com sucesso. FAILURE significa que esse nó falhou. RUNNING significa que ainda está executando, volta a perguntar no próximo tick.

A informação sobe pela árvore. Cada nó pai decide o que fazer com base no resultado dos filhos.

Nada na BT roda em paralelo por padrão. A cada instante, exatamente um caminho da raiz até uma folha está ativo.

#### Tipos de nó fundamentais

Sequence (AND lógico) executa filhos em ordem. Filho retorna SUCCESS, vai para o próximo. Filho retorna FAILURE, para tudo, retorna FAILURE. Filho retorna RUNNING, para tudo, retorna RUNNING (próximo tick volta nesse mesmo filho). Exemplo: ir_até_pallet, pegar_pallet, ir_até_doca. Se qualquer um falhar, missão falhou.

Selector / Fallback (OR lógico) executa filhos em ordem. Filho retorna FAILURE, tenta o próximo. Filho retorna SUCCESS, para tudo, retorna SUCCESS. Filho retorna RUNNING, para tudo, retorna RUNNING. Exemplo: replanejar OU girar OU dar ré OU abortar. Para no primeiro que funcionar.

RecoveryNode é especialização de Selector com retry. Se primeiro filho falhar, executa segundo filho (recovery). Se recovery funcionar, reseta e tenta primeiro filho de novo. Limite configurável de retries.

RoundRobin faz rodízio. Cada vez que é acionado, executa um filho diferente da lista (Spin, Wait, BackUp, Spin, ...).

Decoradores modificam comportamento do filho. RateController(N Hz) limita frequência de execução do filho. Se chamado antes do intervalo, retorna SUCCESS sintético sem chamar filho. Retry(N) se filho falhar, tenta de novo até N vezes. Timeout(t) se filho não terminar em t segundos, retorna FAILURE. Inverter inverte resultado: SUCCESS vira FAILURE e vice-versa.

#### Por que XML e não código

Toda a árvore é declarada em XML. Sem recompilar: mudar a estratégia é editar o XML. Visualmente inspecionável: ferramentas (Groot, Foxglove) renderizam o XML como árvore gráfica. Reutilizável: mesmo XML roda em robôs diferentes, só muda parâmetros das folhas. Acessível para não-programadores: editar BT não exige saber C++.

Análogo industrial: ladder logic de CLP. Mesma filosofia — lógica declarativa, manutenção fácil, sem código procedural.

#### Folhas chamam outros nós ROS 2 via ações

As folhas da BT (ComputePathToPose, FollowPath, Spin) são clientes que invocam OUTROS nós ROS 2 da stack Nav2 via ações.

Folha BT ComputePathToPose invoca nó ROS 2 /planner_server. Função: roda A* (Hybrid-A*) e retorna caminho.

Folha BT FollowPath invoca nó ROS 2 /controller_server. Função: roda MPPI e publica /cmd_vel.

Folhas BT Spin, BackUp, Wait invocam nó ROS 2 /behavior_server. Função: comportamentos de recovery.

Folha BT ClearLocalCostmap invoca service no /local_costmap. Função: limpa costmap local.

O bt_navigator é o MAESTRO que orquestra os outros nós ROS 2.

### A BT padrão do Nav2 (simplificada)

Estrutura:

RecoveryNode (até 6 retries) tem dois filhos: PipelineSequence (caminho normal) e RoundRobin (recovery).

PipelineSequence tem dois filhos: RateController (1 Hz) e FollowPath. RateController tem um filho: ComputePathToPose, que chama /planner_server (A*). FollowPath chama /controller_server (MPPI).

RoundRobin tem três filhos em rodízio: Spin (gira 90°, ~3 s), Wait (espera 5 s), BackUp (ré 30 cm, ~1-2 s).

Tradução em linguagem natural: Tenta navegar até o goal. A cada 1 segundo, replaneja o caminho (RateController estrangulando o A*). Segue o caminho com MPPI. Se falhar 1 vez: entra em recovery (gira, depois espera, depois ré, em rodízio). Se conseguir sair: volta a tentar caminho normal. Se falhar 6 vezes seguidas: aborta missão.

### Por que ticar 10 Hz mas replanejar só 1 Hz (RateController em detalhe)

Conflito aparente: a árvore é avaliada 10x/s, mas o A* é caro (30-100 ms) e o caminho não muda 10x/s. Solução: RateController.

Mecanismo interno do RateController(1 Hz): No primeiro tick após passar 1 segundo, chama o filho e retorna o que o filho retornou (SUCCESS/FAILURE/RUNNING). No tick dentro da janela de 1 s, NÃO chama o filho e retorna SUCCESS sintético — finge que o filho terminou.

Por que retorna SUCCESS sintético e não RUNNING? Porque a Sequence acima precisa receber algo para decidir o próximo passo. Se retornasse RUNNING, a Sequence ficaria parada esperando — e nunca chamaria o FollowPath.

A lógica: "o último plano que recebi ainda é válido (passou só 100 ms), então posso fingir SUCCESS para a árvore seguir adiante e o FollowPath continuar usando o plano antigo."

### Fluxo completo: 8 passos com timing

Cenário 1: navegação normal com sucesso (passos 1-5). Cenário 2: navegação com falha e recovery (passos 6-8).

Passo 1, t=0.0 s. Caminho ativo: Recovery, Pipeline, Rate, Compute. Duração: ~80 ms (A* rodou). /cmd_vel: 0 m/s. O que aconteceu: Início. RateController primeira vez, libera ComputePathToPose. A* roda no /planner_server em ~50 ms, devolve caminho de ~80 pontos. SUCCESS.

Passo 2, t=0.0 s +80 ms. Caminho ativo: Recovery, Pipeline, FollowPath. Duração: +1 ms. /cmd_vel: 0.3 m/s. O que aconteceu: RateController repassa SUCCESS. Sequence vai para FollowPath. Aciona MPPI no /controller_server, que começa a publicar /cmd_vel a 20 Hz. RUNNING.

Passo 3, t=0.1 s. Caminho ativo: Recovery, Pipeline, Rate (sintético), FollowPath. Duração: ~2 ms (sem A*). /cmd_vel: 0.4 m/s. O que aconteceu: RateController: só 100 ms passados, NÃO chama Compute. Retorna SUCCESS sintético. Sequence avança para FollowPath, RUNNING.

Passo 4, t=1.0 s. Caminho ativo: Recovery, Pipeline, Rate, Compute, FollowPath. Duração: ~50 ms (A* rodou). /cmd_vel: 0.5 m/s. O que aconteceu: RateController libera. Compute chama A* de novo. Plano atualizado. FollowPath continua. 9 ticks rápidos sem A* entre 0.1s e 1.0s.

Passo 5, t=5.0 s. Caminho ativo: Recovery, Pipeline, FollowPath (SUCCESS). Duração: ~3 ms. /cmd_vel: 0 m/s. O que aconteceu: FollowPath: distância < tolerância. SUCCESS. Sequence retorna SUCCESS. Recovery retorna SUCCESS. Missão completa.

Passo 6, t=3.0 s (cenário alternativo). Caminho ativo: Recovery, Pipeline, FollowPath (FAILURE). Duração: ~3 ms. /cmd_vel: 0 m/s. O que aconteceu: MPPI não conseguiu seguir. FollowPath retorna FAILURE. Sequence corta e retorna FAILURE.

Passo 7, t=3.0 s + alguns ms. Caminho ativo: Recovery, RoundRobin, Spin. Duração: ~3 s (Spin gira). /cmd_vel: ω=1 rad/s. O que aconteceu: RecoveryNode tenta segundo filho. RoundRobin executa Spin. ~30 ticks de 10 Hz veem Spin RUNNING. SUCCESS quando termina.

Passo 8, t=6.0 s. Caminho ativo: Recovery, Pipeline, Rate, Compute, FollowPath. Duração: ~50 ms. /cmd_vel: sai de novo. O que aconteceu: RoundRobin SUCCESS. Recovery reseta. RateController sem memória, chama Compute. Plano novo (pose diferente após Spin). FollowPath retoma.

### Padrão de timing em 1 segundo de operação normal

Tick da BT inteira: 10 vezes por segundo, duração de 2 a 80 ms cada. Tick com A* rodando: 1 vez por segundo, duração 30-100 ms. Tick sem A* (RateController bloqueou): 9 vezes por segundo, duração ~2 ms cada. Comando publicado em /cmd_vel pelo MPPI: 20 vezes por segundo, continuamente. Loop interno de motor (PID no diff_drive): 100 vezes por segundo, ~1 ms cada.

Os três loops (1 Hz planejador, 20 Hz controller, 100 Hz executor) rodam em PROCESSOS ROS 2 DIFERENTES, em paralelo. BT não bloqueia MPPI, MPPI não bloqueia controle de motor. Cada um na sua frequência, conectado pelos tópicos.

### Por que isso importa para diagnóstico

Sintoma: robô gira a cada poucos segundos sem chegar. Hipótese: /planner_server crashou; ComputePathToPose dá timeout em FAILURE; entra em recovery em loop. Onde investigar: ros2 node list para ver se planner_server está vivo.

Sintoma: robô segue caminho desatualizado por muito tempo. Hipótese: RateController configurado em frequência muito baixa (ex: 0.1 Hz). Onde investigar: nav2_params.yaml parâmetro do RateController.

Sintoma: robô não dá ré em situação travada. Hipótese: BT XML não inclui BackUp no RoundRobin. Onde investigar: editar behavior_trees/navigate_to_pose.xml.

Sintoma: robô faz spin sem sentido em loop. Hipótese: RoundRobin do recovery configurado errado. Onde investigar: editar XML da BT.

### Perguntas de verificação (Behavior Tree)

1. Por que existem DOIS componentes no Loop 1 e não um só algoritmo?

2. Qual a diferença entre "nó ROS 2" e "nó de Behavior Tree"?

3. Qual a diferença prática entre Sequence e Selector? Dá um exemplo de quando usar cada um.

4. Por que o RateController retorna SUCCESS sintético em vez de RUNNING quando estrangula o filho?

5. Se o /planner_server estivesse desligado, o que aconteceria quando ComputePathToPose fosse chamado?

6. Por que replanejar a cada 1 segundo em vez de planejar uma vez no início e seguir?

7. O que aconteceria se o RateController fosse trocado para 0.1 Hz (replan a cada 10 segundos)?

Respostas corretas:

1. São tipos diferentes de problema. BT resolve LÓGICA de decisão (sequência, alternativas, recovery). A* resolve GEOMETRIA de caminho (busca em grafo). Juntar tudo seria monstruoso e impossível de debugar.

2. Nó ROS 2 = processo do SO, aparece em ros2 node list. Nó BT = elemento do XML, vive na memória do bt_navigator, não aparece como processo.

3. Sequence = AND, executa em ordem e para no primeiro que falhar. Selector = OR, executa em ordem e para no primeiro que funcionar. Sequence para missão (todos os passos têm que dar certo). Selector para recovery (qualquer opção que funcione resolve).

4. Para a Sequence acima conseguir avançar para o próximo filho (FollowPath). RUNNING travaria a árvore e FollowPath nunca seria chamado.

5. ComputePathToPose teria timeout (~5 s), durante esse tempo retorna RUNNING. Depois retorna FAILURE. Sequence corta e retorna FAILURE. RecoveryNode tenta RoundRobin (Spin, depois Wait, etc.) em loop. Após 6 retries totais, aborta missão.

6. Obstáculos dinâmicos aparecem. Posição real diverge do esperado (derrapagem, drift de odometria). Mapa pode estar sendo atualizado (SLAM). Costmap inflado por sensor pega obstáculos transitórios. Goal pode ter mudado externamente.

7. Em 10 segundos a 0.5 m/s, robô anda 5 m. Obstáculos novos não seriam refletidos no caminho global por muito tempo. Drift acumula muito entre replans (10-30 cm). Quando finalmente replanejasse, o caminho daria pulo súbito. MPPI faria mais esforço compensando caminho desatualizado, gastando CPU igual ou pior.

[A SEGUIR: Componente 2 — SMAC Hybrid-A*]

Em construção. Próxima atualização do caderno cobrirá: como A* básico funciona com Open List e Closed List, por que f = g + h, diferença entre A* básico e Hybrid-A*, primitivas Dubin, analytic expansion, parâmetros principais do rbot.

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
