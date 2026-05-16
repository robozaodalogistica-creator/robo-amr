# 🎯 Plano de Aprendizado para Virar Expert em Robótica

> Plano de 18-24 meses de prática deliberada.
> Objetivo: virar especialista capaz de resolver problemas reais
> em robótica móvel autônoma.
>
> Compromisso: 2-3h/dia em dias úteis + 4-6h em fim de semana.
> Total: ~2000h ao longo do período.
>
> Criado em: 15/05/2026

---

## 🧭 Princípio fundamental

**Não é tempo total. É qualidade do tempo.**

A diferença entre "fazer demo" e "virar expert" está em:
- Resolver problemas que você NÃO sabe resolver
- Errar, descobrir por quê, corrigir
- Documentar o aprendizado
- Avançar para o próximo desafio

---

## 🎯 As 6 fases do plano

### FASE 1 — Mapeamento e Exploração (1-2 meses)

**Objetivo**: dominar SLAM em situações cada vez mais difíceis.

#### Desafios graduais

**1.1 — SLAM em small_warehouse** ✨ próximo desafio
- [ ] Robô liga sem mapa carregado
- [ ] Roda SLAM Toolbox em modo mapping
- [ ] Anda manualmente explorando o galpão
- [ ] Observa loop closure acontecer
- [ ] Salva mapa gerado
- [ ] Compara com mapa pré-existente do rbot

**1.2 — SLAM em ambiente maior (large_warehouse)**
- [ ] Encontrar/baixar mundo Gazebo grande (50×50m)
- [ ] Tentar mapear → vai dar drift maior
- [ ] Parametrizar SLAM Toolbox para ambiente maior
- [ ] Comparar parâmetros antes/depois

**1.3 — SLAM com atores móveis**
- [ ] Adicionar pessoas andando no Gazebo
- [ ] SLAM precisa filtrar dinâmicos
- [ ] Configurar `obstacle_layer` adequadamente
- [ ] Documentar diferenças no mapa

**1.4 — SLAM em ambiente simétrico**
- [ ] Criar mundo com corredores idênticos
- [ ] Robô vai se perder
- [ ] Adicionar AprilTags como referência
- [ ] Configurar `fiducial_slam` ou similar

---

### FASE 2 — Robustez em Condições Adversas (2-3 meses)

**Objetivo**: robô não pode quebrar quando algo dá errado.

#### Simulações realistas

**2.1 — Sensor falha durante navegação**
- [ ] Implementar watchdog em Python
- [ ] Detectar timeout do /scan
- [ ] Parar robô com segurança
- [ ] Notificar operador

**2.2 — Obstáculo aparece de repente**
- [ ] Spawnar caixa no caminho via Gazebo plugin
- [ ] Validar MPPI desvia
- [ ] Testar caso onde não cabe (robô para)

**2.3 — Perda de conexão (Wi-Fi cai)**
- [ ] Robô continua até último goal? Ou para?
- [ ] Implementar política de degradação
- [ ] Documentar trade-offs de cada abordagem

**2.4 — Robô sequestrado (kidnapped robot)**
- [ ] Mover robô manualmente no Gazebo
- [ ] AMCL vai falhar
- [ ] Detectar e tentar relocalizar
- [ ] Testar diferentes estratégias

**2.5 — Bateria descarregando**
- [ ] Simular bateria diminuindo
- [ ] Implementar lógica "volta para base se < 20%"
- [ ] Validar não acaba bateria no meio da operação

---

### FASE 3 — Missão Complexa de Pallet (2-3 meses)

**Objetivo**: implementar caso de uso real do AMR.

**3.1 — Garfo elevador**
- [ ] Adicionar junta prismatic ao URDF
- [ ] Controlador para subir/descer
- [ ] Integração com ros2_control
- [ ] Validar movimento no Gazebo

**3.2 — Detectar pallet com AprilTag**
- [ ] Instalar apriltag_ros
- [ ] Calibrar câmera no URDF
- [ ] Detectar marker em pallet
- [ ] Publicar TF do pallet detectado

**3.3 — Sequência de docking**
- [ ] Aproximar pallet (Nav2 standard)
- [ ] Alinhar com AprilTag (precisão fina)
- [ ] Mover para baixo do pallet
- [ ] Levantar garfo
- [ ] Confirmar carga (sensor de peso ou simulação)

**3.4 — Missão completa pickup→transit→drop**
- [ ] State machine implementando estados
- [ ] Tratamento de falhas em cada estado
- [ ] Notificações de status para operador
- [ ] Recuperação de falhas em meio à missão

---

### FASE 4 — Múltiplos Robôs e Fleet (2-3 meses)

**Objetivo**: orquestrar vários robôs trabalhando juntos.

**4.1 — 2 robôs no mesmo ambiente**
- [ ] Cada robô com namespace próprio
- [ ] TF tree dupla
- [ ] Conflito em corredor estreito
- [ ] Regra de prioridade implementada

**4.2 — Fleet manager**
- [ ] Sistema central distribuindo tarefas
- [ ] Otimização de qual robô faz qual tarefa
- [ ] Balanceamento de bateria
- [ ] Re-roteamento em tempo real

**4.3 — Visualização operacional**
- [ ] Dashboard com todos os robôs
- [ ] Posição, status, missão atual
- [ ] Alertas de falha em tempo real
- [ ] Histórico de operação

---

### FASE 5 — Integração com Sistemas Externos (2-3 meses)

**Objetivo**: robô vira produto vendável conectado ao cliente.

**5.1 — WMS simulado**
- [ ] Sistema fake que manda pedidos
- [ ] Recebe confirmação
- [ ] Persiste em banco de dados (SQLite ou PostgreSQL)
- [ ] Mock de SAP/Oracle/Manhattan

**5.2 — API REST**
- [ ] Endpoint HTTP para enviar missão
- [ ] Webhook para notificar conclusão
- [ ] Autenticação básica (token)
- [ ] Documentação OpenAPI

**5.3 — Dashboard web**
- [ ] Interface para operador (HTML/CSS/JS)
- [ ] Histórico de missões
- [ ] Métricas (tempo médio, falhas, eficiência)
- [ ] Logs filtráveis

---

### FASE 6 — Hardware Real (3-6 meses)

**Objetivo**: tudo isso no robô físico.

**6.1 — Construir robô físico básico**
- [ ] Comprar componentes (~R$ 15-25k)
- [ ] Montar mecanicamente
- [ ] Cabeamento e elétrica
- [ ] Bateria e proteções

**6.2 — Calibrar sensores reais**
- [ ] LiDAR físico (alcance, ruído)
- [ ] IMU físico (bias, drift real)
- [ ] Encoders (resolução, slip)
- [ ] Câmera (calibração intrínseca)

**6.3 — Replicar tudo das fases anteriores**
- [ ] Cada desafio das Fases 1-5 no hardware real
- [ ] Documentar diferenças sim vs real
- [ ] Ajustar parâmetros para hardware

---

## 📋 Conhecimentos paralelos necessários

Não é só rodar simulação. Capital intelectual a construir:

### Programação básica (ler, não escrever)
- [ ] Ler código Python e entender o que faz
- [ ] Ler arquivo YAML e identificar parâmetros
- [ ] Ler C++ e reconhecer estrutura
- [ ] Curso "Python para engenheiros" (15-20h)

### Matemática aplicada
- [ ] Sistemas de coordenadas e transformações
- [ ] Vetores e matrizes (revisão do cálculo)
- [ ] Probabilidade básica (Gaussianas, intervalos)
- [ ] Filtros conceituais (Kalman, EKF, particle)

### Linux e linha de comando
- [ ] Navegar entre pastas (cd, ls, pwd)
- [ ] Editar arquivos (nano, vim básico)
- [ ] Entender processos (ps, top, htop)
- [ ] ssh, git, ros2 comandos
- [ ] Tempo: 20-40h de prática

### Git e versionamento
- [ ] Branches e merge
- [ ] Pull requests
- [ ] Reverter erros (revert, reset)
- [ ] Colaborar com sócio
- [ ] Tempo: 10-20h

### Documentação técnica
- [ ] Ler documentação de pacotes ROS 2
- [ ] Ler e abrir issues no GitHub
- [ ] Pesquisar em fóruns (ROS Discourse, GitHub Discussions)

---

## 🔄 Método de prática deliberada

Para CADA desafio do plano:

### 1. Tentar sozinho primeiro (30 min mínimo)
- Pensa no problema
- Pesquisa documentação
- Tenta implementar
- Erra mesmo

### 2. Comparar com Claude
- Mostra tentativa
- Recebe análise
- Entende **por quê** está diferente

### 3. Implementar versão refinada
- Vê funcionando
- Testa em vários cenários
- Documenta no repo

### 4. Documentar aprendizado
Cada desafio vira documento em `docs/desafios/`:
- O problema
- Primeira tentativa
- O que aprendeu
- Solução final
- Aplicação futura

### 5. Avançar
- Persistência sim, perfeccionismo não
- Não fica preso em um desafio
- Próximo desafio fortalece o anterior

---

## 📊 Como medir progresso

A cada 2 meses, responder honestamente:

- [ ] Consigo resolver problema X sem ajuda direta?
- [ ] Consigo explicar conceito Y para meu sócio?
- [ ] Consigo identificar causa de bug Z em logs?
- [ ] Consigo customizar comportamento W sem tutorial passo-a-passo?

**Se sim**: avança para próximo bloco.
**Se não**: treina mais nesse ponto.

---

## ⏰ Rotina recomendada
