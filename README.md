# Correção de Rotina de Web Scraping — G1/LGPD

Case técnico da 2ª etapa do processo seletivo de Assistente de Pesquisa em Engenharia de Dados - NetLab (Laboratório de Estudos de Internet e Redes, UFRJ).

Relatório técnico completo (diagnóstico, decisões técnicas e avaliação de qualidade de dados): [`docs/relatorio_tecnico.pdf`](docs/relatorio_tecnico.pdf).

## Resumo do diagnóstico

A rotina original coletava resultados de busca do G1 para o termo "LGPD" via `requests` + `BeautifulSoup` sobre o HTML da página, mas retornava poucos ou nenhum registro. A investigação revelou:

- **3 bugs de lógica** no código original (sobrescrita de acumulador entre páginas, `AttributeError` não tratado ao extrair campos, paginação indexada incorretamente).
- **Causa raiz**: a página de busca do G1 usa renderização client-side os resultados são injetados via JavaScript e não estão presentes no HTML estático entregue pelo servidor (confirmado comparando "Ver código-fonte" com o DOM renderizado no navegador).
- **Solução**: migração da extração para consumo direto da API JSON interna usada pela própria interface do G1 (`busca.globo.com/v1/search`), com paginação via `from`/`size` (padrão Elasticsearch). O BeautifulSoup foi mantido, mas reposicionado exclusivamente para limpeza de marcação HTML residual no campo `highlight.body`.

## Estrutura do repositório

```
.
├── docs/
│   └── relatorio_tecnico.pdf      # relatório completo do case
├── src/
│   ├── scraper_g1.py              # coleta, extração e persistência
│   └── llm_recovery.py            # proposta de suporte via LLM
├── tests/
│   ├── test_extracao.py           # testes da extração de campos
│   └── test_stress.py             # testes de robustez (dados malformados)
├── data/
│   ├── amostra_referencia_manual.json   # amostra de referência (avaliação de qualidade)
│   └── coleta_g1_lgpd_20260913_005042.json  # base coletada (1.209 registros, 13/09/2026)
├── requirements.txt
└── .env.example
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

Rodar a coleta completa para o termo "lgpd" e salvar em JSON:

```bash
python -m src.scraper_g1
```

## Testes

```bash
python -m unittest discover -s tests -t .
```

## Avaliação de qualidade dos dados

Amostra de referência de 20 itens, extraída manualmente e comparada com a saída da rotina automatizada (`from=0, size=20`):

| Dimensão | Resultado |
|---|---|
| Completude (título/url/data/página) | 100% |
| Completude (resumo) | 85% (3 ausências legítimas na fonte, n=20) |
| Atualidade | 100% |
| Precisão | 100% |
| Acurácia | 100% |
| Unicidade | 100% |
| Consistência | 100% |
| Rastreabilidade | 100% |

Metodologia completa e evidências em `docs/relatorio_tecnico.pdf`.

## Proposta de suporte via LLM

`src/llm_recovery.py` contém uma proposta técnica (não uma integração de produção) de uso de LLM para apoiar o diagnóstico e a manutenção da coleta, acionada quando o circuit breaker atinge o limite de falhas ou quando a estrutura do JSON diverge do schema esperado. Validação via Human-in-the-Loop: a sugestão do modelo só é promovida para revisão humana (Pull Request) se passar na suíte `tests/test_stress.py`. Controles contra alucinação: proibição explícita de inferir nomes de campos não presentes no JSON fornecido, temperatura fixada em 0.1. Detalhes completos no relatório técnico.

## Limitações conhecidas

- Dependência de um contrato de API não documentado publicamente mudanças no schema de `busca.globo.com/v1/search` podem quebrar a coleta sem aviso.
- Cobertura de testes parcial: `buscar_artigos_com_total` e o circuit breaker de `coletar_todos` ainda não têm testes com mock de rede.
- Espera fixa de 1 segundo entre requisições, sem backoff exponencial.
- Amostra de referência de 20 itens suficiente para prova de conceito, insuficiente para inferência estatística robusta.
- Integração com LLM documentada com exemplo funcional, mas não integrada ao pipeline de produção.

## Autoria

Hellen de Andrade Moura -- case técnico para o processo seletivo NetLab/UFRJ.
