"""
Proposta de suporte via LLM para diagnóstico e manutenção da rotina de coleta.

Este módulo é uma PROPOSTA TÉCNICA com exemplo funcional, não uma integração
completa em produção (conforme especificado no enunciado do case). É acionado em
dois cenários: (1) o circuit breaker de coletar_todos atinge o limite de falhas
consecutivas, ou (2) a estrutura do JSON diverge do schema esperado (KeyError ou
IndexError em buscar_artigos_com_total).

Fluxo de validação (Human-in-the-Loop):
1. O modelo recebe o log de erro, uma amostra do JSON anômalo e o código atual de
   extrair_dados_artigo.
2. A sugestão do modelo é salva em um arquivo transitório e testada automaticamente
   contra a suíte de testes de robustez (tests/test_stress.py).
3. Só é promovida para revisão humana (Pull Request) se passar em todos os testes;
   caso contrário, é descartada e a intervenção manual é sinalizada.

Controles contra alucinação: o prompt proíbe explicitamente supor nomes de campos
não presentes no JSON fornecido, a temperatura é fixada em 0.1 para determinismo
máximo, e nenhum código é incorporado sem passar pelos testes automatizados.
"""

import os
import re
import subprocess

import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
modelo = genai.GenerativeModel("gemini-2.5-pro")


def solicitar_correcao_llm(erro_log, json_capturado, codigo_extracao):
    """Solicita ao modelo uma sugestão de correção com base no erro observado."""
    prompt = (
        "Você é um agente de engenharia de dados.\n"
        f"Erro: {erro_log}\n"
        f"Código atual:\n```python\n{codigo_extracao}\n```\n"
        f"JSON da API:\n```json\n{json_capturado}\n```\n"
        "Regra: use APENAS as chaves presentes no JSON fornecido. "
        "É proibido supor nomes de campos que não estejam explicitamente no JSON. "
        "Retorne somente código Python."
    )
    resposta = modelo.generate_content(prompt, generation_config={"temperature": 0.1})
    return re.search(r"```python\n(.*?)```", resposta.text, re.DOTALL).group(1)


def validar_e_encaminhar(codigo_gerado):
    """Testa a sugestão do modelo antes de promovê-la para revisão humana."""
    with open("temp_extracao.py", "w") as arquivo:
        arquivo.write(codigo_gerado)

    resultado = subprocess.run(
        ["python", "-m", "unittest", "tests/test_stress.py"],
        capture_output=True,
        text=True,
    )
    os.remove("temp_extracao.py")

    if resultado.returncode == 0:
        with open("sugestao_aprovada_llm.py", "w") as arquivo:
            arquivo.write(codigo_gerado)
        print("Aprovado. Aguardando revisão humana (PR).")
    else:
        print("Rejeitado. Intervenção manual necessária.")
