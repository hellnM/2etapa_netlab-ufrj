"""
Rotina de coleta de resultados de busca do G1 via API JSON interna.

Correção da rotina original de web scraping (que utilizava requests + BeautifulSoup
sobre o HTML estático da página de busca). A investigação revelou que os resultados
são renderizados via JavaScript no lado do cliente e não estão presentes no HTML
entregue pelo servidor. A solução migrou a coleta para o consumo direto da API JSON
interna usada pela própria interface do G1 (busca.globo.com/v1/search).

Consulte o relatório técnico completo em docs/relatorio_tecnico.pdf para o
diagnóstico detalhado, as decisões técnicas e a avaliação de qualidade dos dados.
"""

import csv
import json
import time
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://g1.globo.com",
    "Referer": "https://g1.globo.com/",
    "x-tenant-id": "g1",
    "x-track-urls": "false",
}

BUSCA_URL = "https://busca.globo.com/v1/search"

MAX_FALHAS_CONSECUTIVAS = 3


def montar_payload(termo_busca, from_, size):
    """Monta o payload da consulta principal (perfil de busca por recência)."""
    return [
        {
            "search_profile": "sp_g1_globo_com",
            "query": "g1.info_query_recency",
            "params": {
                "q": termo_busca,
                "from": from_,
                "size": size,
            },
        }
    ]


def buscar_artigos_com_total(termo_busca, from_, size):
    """
    Faz uma requisição POST à API de busca do G1.

    Retorna (artigos, total_resultados, sucesso). `sucesso` é False apenas quando
    uma exceção foi de fato levantada (falha técnica) — uma busca legitimamente
    vazia retorna sucesso=True com artigos=[] e total_resultados=0.
    """
    payload = montar_payload(termo_busca, from_, size)

    try:
        resposta = requests.post(BUSCA_URL, headers=HEADERS, json=payload)
        resposta.raise_for_status()

        resposta_json = resposta.json()
        hits = resposta_json[0]["result"]["hits"]

        return hits["hits"], hits["total"]["value"], True

    except requests.exceptions.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON na página from={from_}: {e}")
        return [], 0, False
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição na página from={from_}: {e}")
        return [], 0, False
    except (KeyError, IndexError) as e:
        print(f"Estrutura de resposta inesperada na página from={from_}: {e}")
        return [], 0, False


def extrair_dados_artigo(artigo, pagina, coletado_em):
    """Extrai os campos de interesse de um item bruto retornado pela API."""
    fonte = artigo.get("_source") or {}

    # URL: alguns itens vêm embrulhados em link de rastreamento
    # (measures.globo.com/v1/click?...&u=<url real>). Decodifica quando presente.
    url_bruta = fonte.get("url") or ""
    if "measures.globo.com" in url_bruta:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url_bruta).query)
        url_final = params.get("u", [url_bruta])[0]
    else:
        url_final = url_bruta

    # Resumo: prioridade caption -> summaryBlocks -> highlight.body (HTML limpo)
    resumo = ""
    if fonte.get("caption"):
        resumo = str(fonte["caption"])
    elif isinstance(fonte.get("summaryBlocks"), list):
        textos = [
            str(bloco["text"])
            for item in fonte["summaryBlocks"]
            if isinstance(item, dict)
            for bloco in (item.get("blocks") or [])
            if isinstance(bloco, dict) and bloco.get("text") is not None
        ]
        resumo = " ".join(textos)

    highlight = artigo.get("highlight") or {}
    if not resumo and isinstance(highlight.get("body"), list):
        # Sem strip=True: get_text(strip=True) remove espaços de cada fragmento de
        # texto ANTES de juntá-los, o que cola palavras que ficavam ao lado de tags
        # inline (ex: "à <em>LGPD</em>" viraria "àLGPD"). O .strip() final abaixo já
        # cuida das pontas do texto completo, sem esse efeito colateral.
        resumo = BeautifulSoup(str(highlight["body"][0]), "html.parser").get_text()

    return {
        "titulo": fonte.get("title") or "",
        "resumo": resumo.strip(),
        "data_publicacao": fonte.get("issued") or "",
        "url": url_final,
        "pagina_origem": pagina,
        "coletado_em": coletado_em,
    }


def coletar_todos(termo_busca, tamanho_pagina=10, limite_paginas=None):
    """
    Coleta todos os resultados disponíveis para o termo de busca, paginando via
    from/size (padrão Elasticsearch). Deduplica por _id, pula páginas com falha
    técnica sem interromper a coleta, e possui um disjuntor (circuit breaker) que
    encerra a execução após MAX_FALHAS_CONSECUTIVAS falhas seguidas — garantindo
    que o loop sempre termina mesmo que a API fique indisponível desde o início.
    """
    todos_artigos = []
    ids_vistos = set()
    from_ = 0
    pagina = 1
    falhas_consecutivas = 0
    coletado_em = datetime.now().isoformat()
    total_esperado = float("inf")

    while True:
        if limite_paginas and pagina > limite_paginas:
            break

        artigos, total_resultados, sucesso = buscar_artigos_com_total(
            termo_busca, from_, tamanho_pagina
        )

        if total_resultados > 0:
            total_esperado = total_resultados

        if not artigos:
            if sucesso:
                print(f"Busca concluída: 0 resultados a partir da página {pagina} (from={from_}).")
                break

            falhas_consecutivas += 1
            print(
                f"Aviso: falha técnica na página {pagina} (from={from_}). "
                f"Falhas seguidas: {falhas_consecutivas}/{MAX_FALHAS_CONSECUTIVAS}"
            )

            if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                print(
                    "Erro crítico: limite de falhas consecutivas atingido. "
                    "Abortando coleta e retornando dados parciais."
                )
                break

            from_ += tamanho_pagina
            pagina += 1

            if from_ >= total_esperado:
                break

            time.sleep(1)
            continue

        falhas_consecutivas = 0

        for artigo in artigos:
            id_artigo = artigo.get("_id")
            if id_artigo and id_artigo not in ids_vistos:
                ids_vistos.add(id_artigo)
                todos_artigos.append(extrair_dados_artigo(artigo, pagina, coletado_em))

        from_ += tamanho_pagina
        pagina += 1

        if from_ >= total_esperado:
            break

        time.sleep(1)

    return todos_artigos


def salvar_dados(dados, formato="json"):
    """Salva os dados coletados em CSV ou JSON, com timestamp no nome do arquivo."""
    if not dados:
        print("Operação cancelada: nenhum dado para salvar.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if formato.lower() == "json":
        nome_arquivo = f"coleta_g1_lgpd_{timestamp}.json"
        with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=4)

    elif formato.lower() == "csv":
        nome_arquivo = f"coleta_g1_lgpd_{timestamp}.csv"
        colunas = dados[0].keys()
        with open(nome_arquivo, "w", encoding="utf-8", newline="") as arquivo:
            writer = csv.DictWriter(arquivo, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(dados)

    else:
        print(f"Erro: o formato '{formato}' não é suportado. Use 'json' ou 'csv'.")
        return None

    print(f"Arquivo salvo: {nome_arquivo} ({len(dados)} registros)")
    return nome_arquivo


if __name__ == "__main__":
    dados_coletados = coletar_todos("lgpd", tamanho_pagina=10)
    salvar_dados(dados_coletados, formato="json")
