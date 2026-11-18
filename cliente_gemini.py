"""Cliente Gemini com uma tentativa HTTP por consulta."""

import os
from google import genai
from google.genai import types
import httpx

from configuracao import Configuracao, ErroConfiguracao


class FalhaConsulta(RuntimeError):
    """Falha externa com mensagem segura para o terminal e o relatório."""


def obter_chave(chave=None):
    chave = chave or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not chave or not chave.strip() or chave == "SUA_CHAVE_AQUI":
        raise ErroConfiguracao("Configure GEMINI_API_KEY no terminal. Use --demo para experimentar sem chave e sem rede.")
    return chave


def criar_cliente(config: Configuracao, *, chave=None, http_client=None):
    if genai.__version__ != "3.3.0":
        raise ErroConfiguracao("Instale as dependências validadas: python -m pip install -r requirements.txt (SDK 3.3.0).")
    chave = obter_chave(chave)
    transporte = http_client or httpx.Client(timeout=config.timeout)
    try:
        return genai.Client(
            api_key=chave, enterprise=False,
            http_options=types.HttpOptions(
                api_version="v1", timeout=int(config.timeout * 1_000),
                retry_options=types.HttpRetryOptions(attempts=1),
                httpx_client=transporte,
            ),
        )
    except Exception as falha:
        if http_client is None:
            transporte.close()
        raise ErroConfiguracao("Não foi possível inicializar o cliente Gemini.") from falha


def consultar_gemini(client, **parametros):
    try:
        return client.interactions.create(**parametros)
    except Exception as falha:
        resposta = getattr(falha, "response", None)
        codigo = getattr(falha, "code", None) or getattr(falha, "status_code", None)
        if not isinstance(codigo, int) and resposta is not None:
            codigo = getattr(resposta, "status_code", None)
        if codigo in {401, 403}:
            mensagem = "Autenticação ou acesso negado. Confira a chave e a permissão do modelo."
        elif codigo == 429:
            mensagem = "Cota ou limite de requisições atingido. Confira o uso no Google AI Studio."
        elif codigo == 404:
            mensagem = "Modelo ou recurso não encontrado. Confira --modelo."
        elif isinstance(codigo, int) and codigo >= 500:
            mensagem = "O serviço Gemini está indisponível. Tente novamente mais tarde."
        elif "timeout" in type(falha).__name__.lower() or isinstance(falha, httpx.TimeoutException):
            mensagem = "Tempo limite da consulta atingido."
        elif "connection" in type(falha).__name__.lower() or isinstance(falha, httpx.TransportError):
            mensagem = "Falha de conexão com o Gemini. Confira sua conexão."
        else:
            mensagem = "A consulta ao Gemini falhou. Confira o modelo e a configuração da API."
        # Não reproduzir corpos de exceções, que podem conter dados ou credenciais.
        raise FalhaConsulta(mensagem + " Nenhuma repetição automática foi realizada.") from falha
