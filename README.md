# Bot AI (Python)

Estrutura base para um "cérebro" de IA que coordena ferramentas, memória e execução no desktop/headless.

## Estrutura
- `src/core`: orquestração, loop principal
- `src/adapters`: integrações externas (LLM, APIs)
- `src/drivers`: drivers de SO/desktop
- `src/skills`: habilidades atômicas
- `src/memory`: memória local
- `src/config`: carregamento de config
- `src/channels`: canais de comunicação (WhatsApp, Telegram, etc.)
- `src/daemon_main.py`: daemon (cérebro) em background
- `src/tui_main.py`: TUI cliente simples
- `src/cli.py`: CLI (ex: `turion doctor`)
- `src/setup.py`: wizard de configuração inicial
- `gateway/`: WhatsApp Gateway (Node + Baileys)

## Instalar cérebro no Ubuntu (systemd)
```bash
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

## Instalação remota (curl | bash)
```bash
curl -fsSL http://turion.network/install.sh | sudo bash
```

## Comando de diagnóstico
```bash
turion doctor          # inspeção completa
turion doctor all      # inspeção completa
turion doctor db       # inspeção do banco
```

## Setup inicial
```bash
turion setup
```

## Prompt base
- Template curto em `docs/prompt.md`

## Memória local (PostgreSQL)
- SQL: `docs/postgres.sql`
- Estratégia: `docs/memory.md`

## Rodar manual
```bash
python3 src/daemon_main.py
python3 src/tui_main.py
```

## Variáveis de ambiente
Veja `.env.example`.
