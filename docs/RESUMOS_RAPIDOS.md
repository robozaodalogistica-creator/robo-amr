# Resumos rápidos

Resumos curtos de cada bloco para revisão rápida, sem precisar reler o ESTUDO_DIDATICO completo.

---

## Bloco 2 — Loop 1: o Planejador (1 Hz)

### Em uma frase

O Loop 1 decide "para onde ir e por onde". É composto por DOIS nós ROS que trabalham juntos: a Behavior Tree (estratégia) e o A* (geometria).

### Os dois nós ROS principais

bt_navigator é o nó que executa a Behavior Tree (BT). Tica a árvore 10 vezes por segundo. Decide LÓGICA: "continuar, replanejar, dar ré, esperar, abortar". Análogo a PLC mestre rodando ladder.

planner_server é o nó que roda o algoritmo SMAC Hybrid-A*. Calcula GEOMETRIA: dado um start e um goal, qual o melhor caminho. Análogo a software CAM gerando trajetória CNC.

### Comunicação entre os três nós já estudados

Diagrama em docs/diagramas/01_mapa_nos_estudados.png

global_costmap mantém o mapa de custos atualizado e PUBLICA num tópico contínuo (1-5 Hz).

planner_server ASSINA o tópico do costmap (sempre tem versão atualizada em memória), mas só RODA quando bt_navigator pede.

bt_navigator pede via AÇÃO ROS chamada ComputePathToPose. É cliente-servidor: pergunta "me dá caminho de A até B", recebe a resposta.

Tópico = fluxo contínuo. Ação = pedido e resposta sob demanda.

### Behavior Tree em detalhe

Cada nó da BT retorna SUCCESS, FAILURE ou RUNNING. Informação sobe pela árvore. Tudo serial (esquerda para direita, raiz para folha).

Sequence (AND): executa filhos em ordem. Para no primeiro FAILURE. Para missão (todos passos precisam dar certo).

Selector / Fallback (OR): tenta filhos em ordem. Para no primeiro SUCCESS. Para recovery (qualquer opção que funcione resolve).

RecoveryNode: Selector com retry. Se primeiro filho falhar, executa recovery. Se recovery der certo, reseta e tenta primeiro filho de novo.

RateController(N Hz): estrangula frequência do filho. Tica 10 Hz, mas só chama filho quando passa o intervalo. Nos outros ticks, retorna SUCCESS sintético para a Sequence avançar.

XML, não código: BT é declarada em XML. Mudar estratégia = editar XML, sem recompilar. Análogo a ladder logic de CLP.

Folhas chamam OUTROS nós ROS via ações: ComputePathToPose chama planner_server, FollowPath chama controller_server, Spin/Wait/BackUp chamam behavior_server.

### A* em detalhe

Custo da busca: f = g + h.
- g = custo real já gasto até a célula atual
- h = estimativa do custo restante (linha reta até goal)
- A* expande sempre a célula com MENOR f

Por que g + h e não só g (Dijkstra: lento, sem direção) ou só h (greedy: cai em becos): equilibra investimento já feito + estimativa restante. Garante caminho ótimo E é rápido.

Open List (descobertas, não expandidas) e Closed List (já expandidas, não volta).

Hybrid-A* vs A* básico: cada nó inclui orientação θ, não só (x, y). Vizinhos são primitivas Dubin (trechos curvos respeitando raio mínimo de viragem), não 8 células adjacentes. Caminho gerado é fisicamente seguível.

Analytic expansion: a cada 3-4 expansões, A* tenta um atalho Dubin direto até o goal. Em campo aberto, termina em poucas iterações.

### Inflation vs cost_travel_multiplier

São duas camadas diferentes, em ordem:

inflation_layer mora no global_costmap. PINTA gradiente nas células ao redor de obstáculos (parede = 254, depois 200, 150, 100... até 0 dentro do inflation_radius). Atua na construção do costmap.

cost_travel_multiplier mora no planner_server. PONDERA quanto esses valores pesam quando A* calcula g: g_novo = g_anterior + distância + (custo_célula × multiplier). Atua durante a busca.

Inflation = "onde está marcado como perigoso e quão largo é o gradiente". Multiplier = "quanto o planner liga para esse perigo".

Inspeção: no RViz, ativa display do costmap. Vê o gradiente colorido em volta de obstáculos. Se está estreito, problema é inflation. Se está largo mas A* corta caminho perto da parede, problema é multiplier.

### Parâmetros do nav2_params.yaml para o A*

| Parâmetro | Conexão com o algoritmo |
|---|---|
| minimum_turning_radius | Raio das primitivas Dubin. Diminuir = curvas mais apertadas. |
| angle_quantization_bins | Bins de orientação (72 = 5° por bin). Mais bins = caminho mais suave. |
| reverse_penalty | Multiplicador em g quando expansão é em ré. Aumentar = A* evita ré. |
| change_penalty | Custo extra para mudar direção (frente↔ré). |
| non_straight_penalty | Multiplicador para arcos vs retas. Aumentar = A* prefere reta. |
| cost_travel_multiplier | Quanto A* pondera os valores da inflation. |
| max_iterations | Limite de expansões antes de desistir. |
| max_planning_time | Timeout do planejamento. |
| analytic_expansion_ratio | Tenta atalho Dubin a cada N expansões. Diminuir = mais frequente. |

Todos esses parâmetros são ponderações da função f = g + h. O algoritmo não muda; só a função de custo muda.

### Diagnóstico rápido

A* dá timeout: goal inalcançável; minimum_turning_radius grande demais; inflation muito agressiva; max_iterations baixo.

Caminho passa por dentro de obstáculo: costmap desatualizado (LiDAR não publicando); allow_unknown true em área com obstáculo real não mapeado.

Caminho fisicamente impossível: minimum_turning_radius menor que raio real do chassi.

Robô não passa em corredor que cabe: 1) verifica minimum_turning_radius. 2) inflation_radius. 3) cost_travel_multiplier.

Robô passa raspando paredes: 1) inflation_radius. 2) cost_travel_multiplier.

Robô gira em loop sem chegar: planner_server crashado (verifica ros2 node list).

### Para revisar

Pergunta-chave para validar que internalizou: explique sem olhar a diferença entre inflation_layer e cost_travel_multiplier, e em qual ordem eles atuam.

---
