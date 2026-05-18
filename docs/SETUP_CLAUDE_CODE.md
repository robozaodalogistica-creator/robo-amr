# Setup do Claude Code (sessão local)

Documenta as configurações pessoais do Claude Code aplicadas nesta máquina (não fazem parte do `robo-amr` em si; são preferências do operador). Resumo do que foi alterado:

1. Alias `clauded` no `~/.bashrc`
2. Modelo padrão e nível de esforço fixados em `~/.claude/settings.json`

---

## 1. Alias `clauded`

Adicionado ao final do `~/.bashrc`, logo após os exports do `GZ_SIM_*`:

```bash
alias clauded="claude --dangerously-skip-permissions"
```

### O que faz

Lança o Claude Code **pulando todos os prompts de permissão** — qualquer comando de Bash, edit, write etc. roda sem confirmação. Útil para iterar rápido em tarefas longas sem ter que aprovar cada `colcon build`, `ros2 launch`, edição de arquivo etc.

### Quando NÃO usar

- **Fora de `~/robotica/robo-amr/`** — sem o salvaguarda do permission prompt, um agente equivocado pode mexer em qualquer arquivo. Restrinja o uso ao workspace do projeto.
- **Com mudanças não commitadas** — `--dangerously-skip-permissions` permite edições, deletes e até `rm -rf` sem perguntar. Se algo der errado e seu trabalho ainda não está no git, é perda. Regra prática: rode `git status` antes; se tiver qualquer coisa que você não quer perder, commit (ou stash) primeiro.
- **Em qualquer diretório com segredos** (`~/.ssh`, `~/.aws`, `~/.config/...`) — mesmo motivo.

Para uso normal, prefira `claude` (com prompts ativos). O `clauded` é uma ferramenta de produtividade, não o padrão.

### Backup

Antes de editar `~/.bashrc`, foi gerado backup com timestamp:

```bash
cp ~/.bashrc ~/.bashrc.backup_$(date +%Y%m%d_%H%M)
```

(Backup desta alteração: `~/.bashrc.backup_20260518_1959`.)

---

## 2. `~/.claude/settings.json`

Conteúdo final:

```json
{
  "skipDangerousModePermissionPrompt": true,
  "theme": "dark",
  "model": "claude-opus-4-7",
  "effortLevel": "medium"
}
```

Backup do anterior: `~/.claude/settings.json.backup`.

### Mudança feita

O arquivo já tinha `"model": "claude-opus-4-7"` (correto, pinado em Opus 4.7) e uma chave `"thinkingEffort": "medium"` que **não é uma chave reconhecida pelo Claude Code** — provavelmente foi escrita por engano em uma sessão anterior, não tinha efeito nenhum. Foi substituída por `"effortLevel": "medium"`, que é a chave válida.

### Por que `claude-opus-4-7` e não `"opus"`

O alias `"opus"` mapeia para "o Opus mais recente" e pode mudar quando sair uma versão nova. A ID explícita `claude-opus-4-7` **pina** o modelo: enquanto esta linha estiver no settings, o Claude Code usa Opus 4.7, ponto. Mais previsível para um setup pessoal documentado.

### `effortLevel: medium` vs. `xhigh` (default)

`effortLevel` controla quanto orçamento de raciocínio interno (thinking) o modelo gasta antes de responder. Valores válidos: `low`, `medium`, `high`, `xhigh`. O default é `xhigh` (máximo).

- **`xhigh`**: usa o orçamento máximo. Ideal para problemas algorítmicos, debugging de bug obscuro, design de arquitetura — qualquer coisa onde "pensar mais" muda a resposta. Custa mais tokens.
- **`medium`**: usa um orçamento reduzido. Para tarefas mecânicas — edição de arquivo conforme especificação, atualização de doc, refactor simples, leitura/grep de código — a qualidade da resposta é praticamente indistinguível, e o consumo de tokens (e o custo) cai bastante.

Como o uso predominante neste projeto é editar docs e fazer ajustes incrementais no workspace, `medium` é um default razoável. Quando uma tarefa específica pedir mais raciocínio (ex.: depurar por que o `controller_manager` está falhando), basta sobrescrever pontualmente (ver abaixo) sem mexer no settings.

### Como sobrescrever por sessão

A env var `CLAUDE_CODE_EFFORT_LEVEL` tem precedência sobre o `settings.json`:

```bash
CLAUDE_CODE_EFFORT_LEVEL=xhigh claude   # só esta invocação
# ou:
export CLAUDE_CODE_EFFORT_LEVEL=xhigh   # vale para a shell atual
```

---

## 3. Verificação

### Alias

```bash
# Em uma nova shell (ou após `source ~/.bashrc`):
type clauded
# Esperado: clauded is aliased to `claude --dangerously-skip-permissions'
```

### Modelo e effort no settings.json

```bash
cat ~/.claude/settings.json
# Deve mostrar "model": "claude-opus-4-7" e "effortLevel": "medium"
```

### Env var (se sobrescrita)

```bash
echo "${CLAUDE_CODE_EFFORT_LEVEL:-<não definida — usando settings.json>}"
```

Note que `echo $CLAUDE_CODE_EFFORT_LEVEL` retorna vazio se a env var não estiver exportada — isso é o estado **normal**, porque o valor está vindo do `settings.json`, não da env. A env é só para override.

### Dentro do Claude Code

- `/config` — abre a UI de configuração; mostra o modelo ativo, tema, e outras settings.
- `/model` — troca o modelo ativo para esta sessão (não persiste no settings).
- `/fast` — toggle do Fast Mode (Opus com saída mais rápida; não troca para modelo menor).

> **Aviso:** não existe comando `/effort` no Claude Code. O nível de esforço é configurado **só** via `settings.json` ou pela env var `CLAUDE_CODE_EFFORT_LEVEL`. Se quiser conferir o nível ativo, use `/config` ou inspecione o `settings.json`.
