import unittest

from src.scraper_g1 import extrair_dados_artigo

FIXTURES_STRESS = [
    {},
    {"_source": {"title": None, "url": None, "issued": None, "caption": None}},
    {"_source": {"url": "https://measures.globo.com/v1/click?c=busca-headless&h=123"}},
    {
        "_source": {
            "summaryBlocks": [
                "erro",
                {"blocks": "erro"},
                {"blocks": [{"text": None}]},
                {"blocks": [{"text": 12345}]},
            ]
        }
    },
    {"_source": {"title": "Teste"}, "highlight": {"body": ["Texto com <b>HTML</b> injetado"]}},
]


class TestStressJSON(unittest.TestCase):

    def test_json_completamente_vazio(self):
        resultado = extrair_dados_artigo(FIXTURES_STRESS[0], 1, "2026-09-12")
        self.assertEqual(resultado["titulo"], "")
        self.assertEqual(resultado["resumo"], "")

    def test_valores_explicitamente_nulos(self):
        resultado = extrair_dados_artigo(FIXTURES_STRESS[1], 1, "2026-09-12")
        self.assertEqual(resultado["titulo"], "")

    def test_url_tracking_sem_parametro_u(self):
        resultado = extrair_dados_artigo(FIXTURES_STRESS[2], 1, "2026-09-12")
        self.assertEqual(
            resultado["url"], "https://measures.globo.com/v1/click?c=busca-headless&h=123"
        )

    def test_summary_blocks_corrompido(self):
        try:
            resultado = extrair_dados_artigo(FIXTURES_STRESS[3], 1, "2026-09-12")
            self.assertIsInstance(resultado["resumo"], str)
        except Exception as e:
            self.fail(f"Quebrou com a exceção: {e}")

    def test_highlight_body_limpeza_html_beautifulsoup(self):
        try:
            resultado = extrair_dados_artigo(FIXTURES_STRESS[4], 1, "2026-09-12")
            self.assertEqual(resultado["resumo"], "Texto com HTML injetado")
        except Exception as e:
            self.fail(f"Quebrou com a exceção: {e}")


if __name__ == "__main__":
    unittest.main()
