import unittest

from src.scraper_g1 import extrair_dados_artigo

FIXTURE_ARTIGOS = [
    {
        "_source": {
            "title": "Notícia 1 com Caption prioritário e URL tracking",
            "url": "https://measures.globo.com/v1/click?c=busca&u=https%3A%2F%2Fg1.globo.com%2Fnoticia1",
            "caption": "Resumo vindo do caption",
            "summaryBlocks": [{"blocks": [{"text": "Resumo vindo do block que deve ser ignorado"}]}],
            "issued": "2026-09-08T10:00:00Z",
        }
    },
    {
        "_source": {
            "title": "Notícia 2 com SummaryBlocks isolado e URL direta",
            "url": "https://g1.globo.com/noticia2",
            "summaryBlocks": [{"blocks": [{"text": "Resumo vindo do block"}]}],
            "issued": "2026-09-09T10:00:00Z",
        }
    },
    {
        "_source": {
            "title": "Notícia 3 sem resumo",
            "url": "https://g1.globo.com/noticia3",
            "issued": "2026-09-10T10:00:00Z",
        }
    },
    {
        "_source": {
            "title": "Notícia 4 com highlight HTML",
            "url": "https://g1.globo.com/noticia4",
            "issued": "2026-09-11T10:00:00Z",
        },
        "highlight": {"body": ["Trecho com <em>LGPD</em> e <b>outras tags</b> injetadas."]},
    },
]


class TestExtracaoArtigos(unittest.TestCase):

    def test_decodificacao_url_tracking(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[0], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["url"], "https://g1.globo.com/noticia1")

    def test_url_direta_sem_tracking(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[1], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["url"], "https://g1.globo.com/noticia2")

    def test_extracao_data_publicacao(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[0], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["data_publicacao"], "2026-09-08T10:00:00Z")

    def test_prioridade_resumo_caption(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[0], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["resumo"], "Resumo vindo do caption")
        self.assertNotIn("ignorado", resultado["resumo"])

    def test_fallback_resumo_summary_blocks(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[1], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["resumo"], "Resumo vindo do block")

    def test_fallback_resumo_highlight_body_com_limpeza_html(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[3], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["resumo"], "Trecho com LGPD e outras tags injetadas.")

    def test_fallback_resumo_inexistente(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[2], pagina=1, coletado_em="2026-09-12")
        self.assertEqual(resultado["resumo"], "")

    def test_chaves_dicionario_consistentes(self):
        resultado = extrair_dados_artigo(FIXTURE_ARTIGOS[2], pagina=1, coletado_em="2026-09-12")
        chaves_esperadas = {"titulo", "resumo", "data_publicacao", "url", "pagina_origem", "coletado_em"}
        self.assertEqual(set(resultado.keys()), chaves_esperadas)


if __name__ == "__main__":
    unittest.main()
