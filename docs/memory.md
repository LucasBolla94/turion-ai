# Memória local com PostgreSQL

## Estratégia
1) Mensagem chega
2) Buscar memória relevante (BM25)
3) Resumir localmente
4) Montar prompt curto
5) Chamar Grok somente quando necessário
6) Atualizar perfil periodicamente (manutenção)

## Banco local (PostgreSQL)
- SQL: `docs/postgres.sql`
- Usuário dedicado: `turion`
- Banco dedicado: `turion`

## Segurança recomendada
- Usuário dedicado com permissões mínimas
- DB local apenas (bind 127.0.0.1)
- Senha forte no `DB_PASSWORD`

## Configuração
Defina no `.env`:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `LLM_API_BASE`, `LLM_API_KEY`

## Ajustes de custo
- `MEMORY_MAX_CONTEXT_ITEMS`: limite de itens
- `MEMORY_MIN_RELEVANCE`: cortar itens fracos
- `ROUTING_SHORTCUT_SIM`: reuse respostas similares
- `GROK_WARMUP_MESSAGES`: acelerar adaptação inicial
- `GROK_MAINTENANCE_EVERY`: manutenção periódica

## Como economiza tokens
- **Cache semântico**: perguntas muito parecidas reutilizam resposta recente.
- **Recorte de contexto**: só os itens mais relevantes entram no prompt.
- **Resumo local**: reduz histórico a poucas frases.
- **Manutenção periódica**: Grok só é usado para atualizar perfil em intervalos.
