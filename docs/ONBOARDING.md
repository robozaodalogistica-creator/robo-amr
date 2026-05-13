# Onboarding — robo-amr

> Guia para começar a contribuir. Escrito para quem nunca abriu ROS 2 antes,
> mas já programa.
> Última atualização: 2026-05-13.

Tempo estimado para chegar ao primeiro "robô navegando na sua tela":
**30-60 min** de instalação + **5 min** de comandos.

---

## 1. Pré-requisitos

### 1.1 Hardware

- CPU x86_64 razoável (qualquer i5/Ryzen 5 de ≥2019 serve).
- 16 GB de RAM (8 GB roda apertado).
- 30 GB livres em disco.
- GPU **não é obrigatória** — Gazebo Harmonic roda com renderização por
  software (llvmpipe). Se tiver uma GPU dedicada (NVIDIA/AMD), o GUI fica mais
  fluído.

### 1.2 Sistema operacional

Em ordem de preferência:

1. **Ubuntu 24.04 LTS nativo** — recomendado. ROS 2 Jazzy + Gazebo Harmonic
   são oficialmente suportados em 24.04. É o que roda no servidor (RunPod).
2. **Ubuntu 22.04 LTS nativo** — funciona, mas com caveats. ROS 2 Jazzy não
   tem binários oficiais para 22.04; você precisaria buildar do source
   (várias horas, frágil) ou usar o **Docker oficial do ROS 2 Jazzy**
   (caminho recomendado — ver §3.3).
3. **Windows + WSL2 (Ubuntu 24.04)** — funciona surpreendentemente bem.
   O GUI do Gazebo passa pelo WSLg automaticamente. Detalhes em §3.2.
4. **macOS** — **não recomendado**. ROS 2 não tem suporte oficial para macOS
   há anos. Use Docker (mas a performance gráfica do Gazebo via X11
   forwarding é ruim). Se for a única opção, melhor: SSH no RunPod.

> **Se você nunca instalou Linux**: WSL2 no seu Windows atual é o caminho de
> menor atrito. Em 30 minutos você está pronto, sem dual-boot, sem reinstalar
> nada. Detalhes em §3.2.

### 1.3 Software a ter de antemão

Independente do caminho:

- **Git** (qualquer versão recente).
- **Editor** com bom suporte a Python e ROS: **VS Code** com a extensão
  "ROS" da Microsoft é o default da comunidade. JetBrains PyCharm também
  serve.
- Conta no GitHub (vai precisar de acesso ao repositório).

---

## 2. Acesso ao repositório

```bash
# 1. Pedir acesso ao repo no GitHub (organização robozaodalogistica-creator).
# 2. Configurar uma chave SSH no GitHub (caminho recomendado) ou um PAT.
# 3. Clonar:
git clone git@github.com:robozaodalogistica-creator/robo-amr.git /workspace
cd /workspace
```

> **Importante**: por padrão clonamos em `/workspace` (e os scripts assumem
> esse caminho). Se quiser usar outro diretório, vai precisar editar os
> caminhos em `setup_master.sh`, `start_gui.sh`, `start_amr_gui.sh`. Mais fácil
> ficar com `/workspace`.

---

## 3. Setup local (no seu PC)

Três caminhos. Escolha **um**. Em todos os três, no final você vai ter
ROS 2 Jazzy + Gazebo Harmonic + Nav2 + o repositório buildado.

### 3.1 Ubuntu 24.04 nativo (recomendado)

Este é o caminho mais limpo. Os scripts `setup_master.sh` /
`install_ros2_jazzy.sh` foram desenhados para Ubuntu 24.04 e fazem tudo.

```bash
# Pré-requisitos do próprio script:
sudo apt update
sudo apt install -y curl git sudo

# Roda o provisionamento (idempotente — pode rodar de novo se algo der errado):
sudo /workspace/setup_master.sh
```

O que ele instala (resumo — detalhe no [README](../README.md)):

| Bloco | Conteúdo |
|---|---|
| ROS 2 Jazzy Desktop | base + dev tools (ament, rosdep, colcon) |
| Gazebo Harmonic | sim + ros_gz bridge |
| Nav2 | bringup, MPPI, smoother, behaviors |
| SLAM Toolbox, foxglove_bridge, turtlebot3 sim | extras úteis |
| Node 22 + Claude Code (CLI) | opcional |
| cloudflared | só relevante se for streamar GUI |

Tempo: ~10 min em rede boa. Log completo em `/workspace/setup_master.log`.

**Ao fim**, o script:

- Cria o usuário `dev` (senha `dev123`) — só relevante no container; no seu
  PC pode ignorar.
- Configura o `~/.bashrc` para sourcing automático.
- Builda os 3 workspaces (`amr_pallet`, `nav_test`, `tb3_nav_demo`).

Abra um terminal novo e verifique:

```bash
source /opt/ros/jazzy/setup.bash
source /workspace/amr_pallet/install/setup.bash
ros2 pkg list | grep amr_pallet      # → "amr_pallet"
gz sim --version                     # → "Gazebo Sim, version 8.x"
```

### 3.2 Windows + WSL2 (Ubuntu 24.04)

1. Habilita WSL2 (PowerShell **como admin**):

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

   Reinicia o Windows. Abre o "Ubuntu 24.04" no menu Iniciar — vai pedir
   usuário/senha do Linux.

2. Dentro do Ubuntu (WSL2), os comandos do §3.1 funcionam **iguais**. WSLg
   (incluso no Windows 11 / Windows 10 21H2+) repassa janelas X11 e Wayland
   para o Windows automaticamente — não precisa configurar nada para o
   Gazebo abrir.

3. Caveats específicos do WSL2:

   - **Performance**: WSL2 usa um VHDX em NTFS. Se possível, clone o repo em
     `/home/<seu-user>/workspace` em vez de `/mnt/c/...` — fica 10× mais
     rápido.
   - **GPU**: se sua máquina tem NVIDIA, instale os drivers no Windows e o
     CUDA-on-WSL passa nativo. Não é necessário para o Gazebo
     (llvmpipe basta), mas ajuda muito.
   - **Memória**: por padrão WSL2 reserva 50% da RAM. Para 16 GB de host,
     limite a 8 GB criando `C:\Users\<você>\.wslconfig`:
     ```
     [wsl2]
     memory=8GB
     processors=4
     ```

### 3.3 Docker (qualquer host: Ubuntu 22.04, Linux genérico, macOS, Windows sem WSL)

Caminho mais portável. Penalidade: GUI gráfico fica mais chato (precisa
X11 forwarding ou VNC).

```bash
# Imagem oficial do ROS 2 Jazzy:
docker run -it --rm \
  --net=host \
  -v /workspace:/workspace \
  ros:jazzy-ros-base \
  bash

# Dentro do container, roda o setup_master.sh igual ao §3.1.
```

Para GUI, duas opções dentro do container:

- **X11 forwarding** (Linux host, simples): adicione
  `-e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix`.
- **Streaming via navegador** (qualquer host): rode `start_gui.sh` dentro do
  container — sobe Xvfb + VNC + cloudflared, e te dá uma URL pública.

---

## 4. Setup alternativo: RunPod (servidor compartilhado)

O outro sócio (engenheiro mecânico) trabalha em um container RunPod. Você
pode usar o mesmo se preferir não instalar nada localmente. Custa
~USD 0.5/h ligado.

```bash
# No container fresco do RunPod, como root:
git clone git@github.com:robozaodalogistica-creator/robo-amr.git /workspace
cd /workspace
sudo ./setup_master.sh
```

Depois:

```bash
su - dev          # senha: dev123
# o ambiente já está sourceado
```

Para acessar o GUI do Gazebo via navegador (já que o RunPod é headless):

```bash
/workspace/start_gui.sh
# → imprime uma URL pública (cloudflared). Abre no seu navegador.
```

Vantagens do RunPod:

- Sem instalação local.
- Mesmo ambiente que o outro sócio (zero "na minha máquina funciona").
- Hardware razoável (CPU dedicada, opcionalmente GPU).

Desvantagens:

- Pago por hora ligada.
- Latência para edição de código (mitigada com VS Code Remote-SSH).
- Não dá para usar offline.

**Recomendação**: instale localmente (§3.1 ou §3.2) para o dia-a-dia. Use o
RunPod para experimentos pesados ou para reproduzir o ambiente "oficial" de
testes.

---

## 5. Como clonar e buildar

Assumindo que os pré-requisitos (§3) já estão prontos:

```bash
# 1. Clonar (se ainda não)
git clone git@github.com:robozaodalogistica-creator/robo-amr.git /workspace
cd /workspace

# 2. Sourcing do ROS 2 (em cada shell novo — o setup_master já adiciona ao .bashrc)
source /opt/ros/jazzy/setup.bash

# 3. Build do workspace principal
cd /workspace/amr_pallet
colcon build --symlink-install

# 4. Sourcing do workspace (em cada shell novo)
source /workspace/amr_pallet/install/setup.bash
```

> `colcon build --symlink-install` é o build incremental do ROS 2. O
> `--symlink-install` faz o `install/` apontar para o `src/` via symlink — você
> edita um Python e a mudança aparece sem rebuildar. Para C++ ainda precisa
> rebuildar.

Atalhos definidos no `~/.bashrc` pelo `setup_master.sh`:

```bash
cb     # = colcon build --symlink-install
cbt X  # = colcon build --symlink-install --packages-select X
```

---

## 6. Primeiro experimento: ver o robô navegar

### Opção A — Modo headless (sem Gazebo gráfico)

Mais leve. Você vê só logs e pode espiar no Foxglove pelo navegador.

```bash
# Terminal 1: sobe a stack
ros2 launch amr_pallet warehouse.launch.py

# Terminal 2: abre o Foxglove
# No seu navegador: https://studio.foxglove.dev/
# Conexão: "Open Connection" → "Foxglove WebSocket" → ws://localhost:8765
```

Depois de ~35 s, o `logistics_mission` começa a despachar goals para o Nav2,
e você vê no Foxglove o robô (TF + costmaps) percorrendo os 4 pallets.

### Opção B — Modo gráfico (Gazebo)

Mais pesado, mostra o mundo Gazebo de verdade.

```bash
# Terminal 1 (só se estiver no RunPod ou via SSH — pula em PC local com display direto)
/workspace/start_gui.sh

# Terminal 2: sobe Gazebo + Nav2 + missão
/workspace/start_amr_gui.sh start

# Status / logs / parar
/workspace/start_amr_gui.sh status
/workspace/start_amr_gui.sh logs
/workspace/start_amr_gui.sh stop
```

Se rodou `start_gui.sh`, ele imprime uma URL pública (via cloudflared). Abre
no navegador e você vê o desktop com Gazebo. No PC local com display direto,
o Gazebo abre como qualquer aplicação.

---

## 7. Primeiros comandos úteis

```bash
# Ver tópicos publicados:
ros2 topic list

# Espiar uma mensagem:
ros2 topic echo /odom --once

# Ver TF tree:
ros2 run tf2_tools view_frames    # gera frames.pdf no diretório atual

# Listar action servers:
ros2 action list

# Mandar um goal manual (anda 2 m à frente):
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.0}, orientation: {w: 1.0}}}}"

# Ver parâmetros do controller:
ros2 param list /controller_server

# Ver pacotes instalados:
ros2 pkg list | wc -l    # ~330 pacotes em Jazzy Desktop
```

---

## 8. Onde mexer (mapa-tour do código)

| Quero mudar… | Edita… |
|---|---|
| Comportamento do robô (cinemática) | [`amr_pallet/src/amr_pallet/amr_pallet/robot_sim.py`](../amr_pallet/src/amr_pallet/amr_pallet/robot_sim.py) |
| Missão (waypoints, ordem) | [`amr_pallet/src/amr_pallet/amr_pallet/logistics_mission.py`](../amr_pallet/src/amr_pallet/amr_pallet/logistics_mission.py) |
| Parâmetros do Nav2 (velocidades, costmap, planner) | [`amr_pallet/src/amr_pallet/config/nav2_params.yaml`](../amr_pallet/src/amr_pallet/config/nav2_params.yaml) |
| Mundo Gazebo (paredes, pallets, doca) | [`amr_pallet/src/amr_pallet/worlds/galp_amr.world`](../amr_pallet/src/amr_pallet/worlds/galp_amr.world) |
| Aparência do robô (cosmética) | [`amr_pallet/src/amr_pallet/models/amr_viz/model.sdf`](../amr_pallet/src/amr_pallet/models/amr_viz/model.sdf) |
| Mapa 2D (occupancy grid) | [`amr_pallet/src/amr_pallet/maps/warehouse.yaml`](../amr_pallet/src/amr_pallet/maps/warehouse.yaml) + `.pgm` |
| Como os nós sobem juntos | [`amr_pallet/src/amr_pallet/launch/warehouse.launch.py`](../amr_pallet/src/amr_pallet/launch/warehouse.launch.py) |

Depois de mexer em Python: como o build é `--symlink-install`, basta
reiniciar o nó (Ctrl+C no launch e rodar de novo). Para C++ ou para mudar
qualquer coisa no `setup.py` / `package.xml`: `cb` ou `cbt amr_pallet`.

---

## 9. Próximos passos sugeridos para se ambientar

Em ordem crescente de "mete a mão":

1. **Rode a missão completa** (§6). Veja o robô andar pelos 4 pallets.
2. **Mude um waypoint** no `logistics_mission.py:33-40`. Reinicie o launch.
3. **Mude a velocidade máxima** em `nav2_params.yaml:43` (`max_vel_x`).
   Veja a diferença.
4. **Leia o [`ROBOT_ANALYSIS.md`](ROBOT_ANALYSIS.md)** inteiro — é o melhor
   raio-X do que o sistema é hoje.
5. **Escolha uma tarefa da seção 9 do ROBOT_ANALYSIS** ("trivial" ou "baixo")
   e implemente. As mais didáticas:
   - Adicionar IMU virtual no `amr_viz` (plugin já está carregado, é só
     declarar o sensor no SDF + criar um bridge).
   - Trocar o footprint disco por polígono retangular.
6. **Conversar com o outro sócio** sobre qual é o próximo passo de Fase 1 ou
   Fase 2 do roadmap (ver [`README.md`](../README.md)).

---

## 10. Quando algo der errado

- Log de instalação: `/workspace/setup_master.log`.
- Logs dos serviços do `start_amr_gui.sh`: `/tmp/amr_gui/*.log`.
- Logs do streaming GUI: `/tmp/gui_stream/*.log`.
- ROS 2 logs: `~/.ros/log/<timestamp>/`.
- `setup_master.sh` é idempotente — pode rodar de novo, só executa o que
  faltou. Não tem risco de "quebrar de novo o que já funcionava".
- Build incremental quebrou de um jeito esquisito (raro): apague `build/` e
  `install/` e roda `cb` de novo.

Se precisar de ajuda, manda no chat com:

1. Comando que você rodou.
2. Stack-trace completo (não corta).
3. Output de `ros2 doctor --report`.

---

## 11. Referências

- [`/workspace/README.md`](../README.md) — visão do produto + roadmap.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — decisões de stack e limitações.
- [`ROBOT_ANALYSIS.md`](ROBOT_ANALYSIS.md) — análise técnica do robô atual.
- [ROS 2 Jazzy docs](https://docs.ros.org/en/jazzy/) — referência oficial.
- [Nav2 docs](https://docs.nav2.org/) — referência da stack de navegação.
- [Gazebo Harmonic docs](https://gazebosim.org/docs/harmonic) — sim.
