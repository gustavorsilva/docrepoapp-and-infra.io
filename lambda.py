import requests
import re
import base64
import os
from typing import List, Dict, Optional, Tuple  # <-- IMPORT NECESSÁRIO

# ===== CONFIGURAÇÕES =====
USERNAME = "gustavorsilva"          # usuário ou org do GitHub
TOKEN = os.getenv("GITHUB_TOKEN")
FILTRO = "lambda"
OUTPUT_FILE = "resultados.md"

HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
REQUEST_TIMEOUT = 10.0

# Regras de versões esperadas conforme origem
VERSOES_ATUALIZADAS = {
    "github.com/sua-organizacao/": "v4.0.0",
    "github.com/sua-empresa/": "v6.0.0",
}

SOURCE_REGEX = r'source\s*=\s*"git::([^"]+)"'
REF_REGEX = r'ref=(v[0-9]+\.[0-9]+\.[0-9]+)'


def extrair_source(conteudo: str) -> List[Dict]:
    results = []
    for match in re.findall(SOURCE_REGEX, conteudo):
        url = match
        ref_match = re.search(REF_REGEX, url)
        versao_atual = ref_match.group(1) if ref_match else None
        results.append({"url": url, "versao_atual": versao_atual})
    return results


def detectar_versao_esperada(url: str) -> Optional[str]:
    for origem, versao in VERSOES_ATUALIZADAS.items():
        if origem in url:
            return versao
    return None


def listar_repos(usuario: str) -> List[Dict]:
    repos = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/users/{usuario}/repos?per_page={per_page}&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if resp.status_code != 200:
            print("Erro ao consultar repositórios:", resp.status_code, resp.text)
            break

        data = resp.json()
        if not data:
            break

        repos.extend(data)
        if len(data) < per_page:
            break

        page += 1

    return repos


def listar_arquivos(repo_owner: str, repo_name: str, branch: str) -> List[Dict]:
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        return []
    return resp.json().get("tree", [])


def baixar_arquivo(repo_owner: str, repo_name: str, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        return None

    data = resp.json()
    if "content" in data and data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            return None

    return None


def gerar_markdown(resultados: List[Dict], output_file: str):
    with open(output_file, "w", encoding="utf-8") as md:
        md.write("# Relatório de análise de source nos arquivos .tf\n\n")

        for item in resultados:
            md.write(f"## Repositorio: {item['repo']}\n")
            md.write(f"- Arquivo: `{item['arquivo']}`\n\n")

            for src in item["sources"]:
                url = src["url"]
                versao_atual = src["versao_atual"]
                versao_esperada = detectar_versao_esperada(url)

                if versao_atual and versao_esperada:
                    atualizado = versao_esperada ==  versao_atual
                else:
                    atualizado = False

                md.write(f"- URL: `{url}`\n")

                if versao_atual is None:
                    md.write("- Status: Versao atual não encontrada\n\n")
                    continue

                if versao_esperada is None:
                    md.write("- Status: Origem desconhecida, sem regra de versão\n\n")
                    continue

                if atualizado:
                    md.write(f"- Status: Atualizado (Versao atual: `{versao_atual}`)\n\n")
                else:
                    md.write(
                        f"- Status: Desatualizado (Versao atual: {versao_atual} | Versao recomendada: {versao_esperada})\n\n"
                    )


def main():
    repos = listar_repos(USERNAME)

    if not repos:
        print("Nenhum repositório retornado.")
        return

    resultados = []

    for repo in repos:
        nome = repo.get("name")
        if not nome:
            continue


        if FILTRO.lower() not in nome.lower():
            continue

        branch = repo.get("default_branch", "main")

        print("Analisando repo:", nome)

        arquivos = listar_arquivos(USERNAME, nome, branch)
        tf_files = [a["path"] for a in arquivos if a.get("path", "").endswith(".tf")]

        for tf in tf_files:
            conteudo = baixar_arquivo(USERNAME, nome, tf)
            if conteudo is None:
                continue

            sources = extrair_source(conteudo)

            if sources:
                resultados.append({
                    "repo": nome,
                    "arquivo": tf,
                    "sources": sources
                })

    gerar_markdown(resultados, OUTPUT_FILE)
    print("Arquivo gerado:", OUTPUT_FILE)

if __name__ == "__main__":
    main()