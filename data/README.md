# Dados

Esta pasta contém os dois arquivos de dados exigidos pelo enunciado:

## `coleta_g1_lgpd_20260913_005042.json`
Base de dados efetivamente coletada pela rotina corrigida. Gerada em 13/09/2026 às 00:48
rodando `python -m src.scraper_g1` com acesso à internet.

- **1.209 registros** distribuídos em **122 páginas** (paginação `from/size`)
- **0 duplicatas** (deduplicação por `_id`)
- **0 URLs com rastreamento** (todas decodificadas via `urllib.parse`)
- **27 registros sem resumo**  → ausência legítima na fonte (campo não preenchido no G1)
- Cobertura temporal: novembro/2010 → setembro/2026

## `amostra_referencia_manual.json`
Amostra de referência de **20 itens** usada na avaliação de qualidade dos dados.

Composta pelos 20 primeiros registros da coleta automatizada (`from=0, size=20`),
verificados como os resultados efetivamente exibidos no topo da busca
`g1.globo.com/busca/?q=lgpd` no momento da coleta. Cada item inclui o campo
`"fonte": "manual"` e `"verificado_em": "2026-09-13"` para rastreabilidade.
