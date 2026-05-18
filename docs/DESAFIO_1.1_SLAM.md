# Desafio 1.1 — SLAM em small_warehouse

## Objetivo

Primeiro desafio da Fase 1 do plano de aprendizado (ver [PLANO_APRENDIZADO_EXPERT.md](PLANO_APRENDIZADO_EXPERT.md), seção "1.1 — SLAM em small_warehouse"):

- [x] Robô liga sem mapa carregado
- [x] Roda SLAM Toolbox em modo mapping
- [x] Anda manualmente explorando o galpão
- [x] Observa loop closure acontecer
- [x] Salva mapa gerado
- [x] Compara com mapa pré-existente do rbot — *não existe no repo (ver seção "Comparação com mapa do rbot"); achado documentado, item considerado resolvido*

**Status:** ✅ Concluído em 2026-05-18.

## Estado inicial

- 9 pacotes do workspace `robo-amr` compilados.
- Stack subia parcialmente, mas SLAM não inicializava: o Gazebo abria sem as malhas do robô e o `controller_manager` falhava por ausência do plugin de hardware.

## Problemas encontrados

### a) `rlai_meshes` não foi compilado no build inicial

O pacote de malhas ficou de fora do primeiro `colcon build`, então o `install/rlai_meshes/share` não existia e nada que dependia das `.stl` carregava.

**Fix:**
```bash
colcon build --packages-select rlai_meshes
```

### b) `GZ_SIM_RESOURCE_PATH` não incluía o workspace local

Mesmo após compilar `rlai_meshes`, o Gazebo não encontrava os arquivos `.stl` porque a variável de ambiente só apontava para os caminhos padrão do sistema, sem o `install/` do workspace.

**Sintoma:** Gazebo abre sem geometria do robô / mundo incompleto.

### c) `GZ_SIM_SYSTEM_PLUGIN_PATH` estava vazia

A variável estava unset, então o plugin `gz_ros2_control-system` (necessário para o `controller_manager` falar com o Gazebo) não era encontrado.

**Sintoma:** `controller_manager` não sobe; sem controllers, o robô não responde a comandos e o SLAM fica sem `/odom` e `/scan` consistentes.

## Solução temporária (sessão atual)

Exports manuais no shell antes de lançar a simulação:

```bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$HOME/robotica/robo-amr/install/rlai_meshes/share:$HOME/robotica/robo-amr/install/rlai_description/share
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/jazzy/lib
```

## Solução permanente

Adicionar os mesmos exports ao `~/.bashrc`, **depois** das linhas que sourceiam `/opt/ros/jazzy/setup.bash` e `install/setup.bash` do workspace, para que toda nova shell já saia configurada.

Backup criado antes da alteração: `~/.bashrc.backup_20260518`.

## Comando final que funcionou

```bash
ros2 launch rlai_bringup simulation.launch.py mapping_enabled:=true slam_rviz_enabled:=true
```

## Validação

`ros2 node list` retornou 20 nós, incluindo os críticos:

- `controller_manager` — plugin do Gazebo carregou
- `slam_toolbox` — SLAM em modo mapping ativo
- `ekf_node` — fusão de odometria rodando

Stack completa de pé, SLAM produzindo mapa.

## Como dirigir o robô

Com a simulação rodando (`mapping_enabled:=true`), em **outro terminal**:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
```

O parâmetro `stamped:=true` publica `geometry_msgs/TwistStamped` em `/cmd_vel` (formato esperado pelo `velocity_smoother`/controlador deste stack; sem ele o robô não responde).

Mapa de teclas (padrão do nó):

```
   u    i    o       ↖ frente-esq | ↑ frente   | ↗ frente-dir
   j    k    l       ← gira esq   | ■ para     | → gira dir
   m    ,    .       ↙ ré-esq     | ↓ ré       | ↘ ré-dir
```

Teclas principais usadas no desafio:

- `i` — frente
- `,` — ré
- `j` — girar esquerda
- `l` — girar direita
- `k` — parar

Velocidade: `q`/`z` aumenta/diminui ambas (linear + angular); `w`/`x` só linear; `e`/`c` só angular.

## Loop closure

**O que é:** quando o SLAM reconhece que o robô voltou a uma área já mapeada, ele corrige a trajetória acumulada (e o mapa inteiro) para fechar o "laço". Sem isso, o erro de odometria/giroscópio se acumularia indefinidamente e duas passagens pelo mesmo corredor desenhariam paredes duplicadas.

**Como provocar:** dirija o robô em um trajeto fechado — saia de um ponto, dê a volta pelo galpão e retorne ao ponto de partida (ou cruze uma região já visitada vindo de outro ângulo).

**Como reconhecer no RViz:** o mapa dá um "ajuste súbito" — paredes que estavam ligeiramente deslocadas/duplicadas se realinham de uma vez, e a trajetória do robô (visível no grafo de poses do SLAM Toolbox) reorganiza-se. É instantâneo, dura um frame.

## Como salvar o mapa

Com o SLAM ainda rodando e o mapa em estado satisfatório, em outro terminal:

```bash
ros2 run nav2_map_server map_saver_cli -f maps/NOME
```

Isso gera dois arquivos no diretório atual:

- `maps/NOME.pgm` — imagem da grade de ocupação (PGM em escala de cinza)
- `maps/NOME.yaml` — metadados (resolução, origem, thresholds) que o `map_server` consome

O caminho passado a `-f` é **sem extensão**; o utilitário acrescenta `.pgm` e `.yaml`. Rodar a partir da raiz do workspace garante que os arquivos caem em `robo-amr/maps/`.

Mapa gerado nesta sessão: `maps/small_warehouse_france.pgm` + `.yaml` (791×731 px @ 0.05 m/px ⇒ ~39.6×36.6 m, origem `[-13.873, -16.292, 0]`).

## Comparação com mapa do rbot

**Achado:** o `rbot` **não inclui** um mapa pré-construído do `small_warehouse`. O arquivo `src/rbot/mapping/rlai_mapping/config/map_server.yaml` define `yaml_filename: ""` (placeholder vazio, com a nota "must be overridden by launch arguments"), e não existe nenhum `.pgm` dentro de `src/rbot/`. O fluxo previsto pelo stack é: rodar SLAM, salvar mapa, depois passá-lo via `map_yaml_file:=...` para `localization_amcl.launch.py` ou `map_server.launch.py`.

Portanto, não há comparação 1:1 a fazer com "o mapa do rbot". O mapa salvo nesta sessão (`small_warehouse_france.*`) é, por enquanto, o único do `small_warehouse` no workspace.

Para contexto, outros mapas presentes no workspace (de pacotes adjacentes, **mundos diferentes** — não comparáveis ao `small_warehouse`):

| Mapa | Pacote | Dimensão (px) | Dimensão (m) | Área (m²) | Origem |
|---|---|---|---|---|---|
| `small_warehouse_france` | `maps/` (este desafio) | 791×731 | 39.55 × 36.55 | ~1446 | [-13.873, -16.292] |
| `warehouse` | `amr_pallet` | 400×300 | 20.0 × 15.0 | 300 | [-10.0, -7.5] |
| `galp_amr` | `amr_pallet` | 200×160 | 10.0 × 8.0 | 80 | [-5.0, -4.0] |
| `tb3_world` | `tb3_nav_demo` | 384×384 | 19.2 × 19.2 | ~369 | [-10.0, -10.0] |
| `free_space` | `nav_test` | 200×200 | 10.0 × 10.0 | 100 | [-5.0, -5.0] |

Todos usam a mesma resolução padrão do `slam_toolbox` (0.05 m/px). O `small_warehouse_france` é claramente o maior — coerente com o `small_warehouse` do Gazebo, que é um galpão de algumas dezenas de metros, enquanto os demais cobrem cenas menores ou mundos distintos (TurtleBot3 world, galpões customizados de outros estudos).

## Lições aprendidas

Três bugs de configuração do Gazebo bloquearam a stack inicialmente. Os três valem como checklist para qualquer setup novo deste workspace:

1. **`rlai_meshes` precisa estar compilado.** Se o pacote ficar fora do `colcon build`, nada que dependa das `.stl` carrega — o Gazebo abre sem geometria. Fix: `colcon build --packages-select rlai_meshes` (ou um build completo).
2. **`GZ_SIM_RESOURCE_PATH` precisa incluir o `install/` do workspace.** O Gazebo só procura malhas nos caminhos do sistema por padrão; sem apontar para `install/rlai_meshes/share` e `install/rlai_description/share`, o mundo sobe vazio.
3. **`GZ_SIM_SYSTEM_PLUGIN_PATH` precisa apontar para `/opt/ros/jazzy/lib`.** Sem ela o plugin `gz_ros2_control-system` não é encontrado, o `controller_manager` não sobe e o robô não responde a `/cmd_vel` — o SLAM até roda, mas sem odometria útil.

Os três exports foram persistidos no `~/.bashrc` para que toda shell nova já saia configurada (ver seção "Solução permanente").

## Próximo passo

- Carregar o mapa salvo via AMCL (`use_amcl:=true map_yaml_file:=$(pwd)/maps/small_warehouse_france.yaml`) e validar localização sem SLAM — base para o Desafio 1.2.
