import requests
import re
import base64
import os
from typing import List, Dict, Optional, Tuple  # <-- IMPORT NECESSÁRIO

# ===== CONFIGURAÇÕES =====
USERNAME = "gustavorsilva"          # usuário ou org do GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
FILTRO = "lambda"
OUTPUT_FILE = "resultados.md"

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# Regex para encontrar runtime, ex: runtime = "python3.10" ou runtime="nodejs18.x"
RUNTIME_REGEX = r'runtime\s*=\s*"([^"]+)"'

REQUEST_TIMEOUT = 10.0

# Versão mínima recomendada (major, minor)
VERSAO_RECOMENDADA_TUPLE: Tuple[int, int] = (3, 12)


def parse_python_version_tuple(runtime: str) -> Optional[Tuple[int, int]]:
    """
    Tenta extrair a versão Python do runtime e retorna (major, minor).
    Exemplos:
      'python3.10' -> (3, 10)
      'python3.9'  -> (3, 9)
      'python3.9.6'-> (3, 9)
      'python312'  -> (3, 12)  (heurística)
      'python3'    -> (3, 0)
    Retorna None se não for possível interpretar como Python com versão.
    """
    rt = runtime.lower()
    if "python" not in rt:
        return None

    # procura dígitos e pontos logo após 'python' (ou em qualquer lugar)
    m = re.search(r'python[^\d]*([0-9]+(?:\.[0-9]+)*)', rt)
    if not m:
        # tenta capturar apenas dígitos na string
        m2 = re.search(r'([0-9]{1,3})', rt)
        if not m2:
            return None
        digits = m2.group(1)
    else:
        digits = m.group(1)

    # se contém ponto, use os dois primeiros segmentos
    if '.' in digits:
        parts = digits.split('.')
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor)
        except ValueError:
            return None

    # sem ponto: heurística
    # ex: "39" -> (3,9) ; "310" -> (3,10) ; "312" -> (3,12)
    if digits.isdigit():
        # se 1 dígito -> major
        if len(digits) == 1:
            return (int(digits), 0)
        # se 2 dígitos -> primeira é major, segunda é minor
        if len(digits) == 2:
            return (int(digits[0]), int(digits[1]))
        # se 3 dígitos -> ex: 312 => major=first, minor=last two
        if len(digits) == 3:
            return (int(digits[0]), int(digits[1:]))
        # caso maior, pegar primeiro e resto
        return (int(digits[0]), int(digits[1:]))

    return None


def format_version_tuple(t: Tuple[int, int]) -> str:
    return f"{t[0]}.{t[1]}"


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

    data = resp.json()
    return data.get("tree", [])


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


def extrair_runtimes_do_conteudo(conteudo: str) -> List[str]:
    return re.findall(RUNTIME_REGEX, conteudo)


def gerar_markdown(resultados: List[Dict], output_file: str):
    with open(output_file, "w", encoding="utf-8") as md:
        md.write("# Resultados da análise dos arquivos .tf\n\n")

        if not resultados:
            md.write("Nenhum runtime encontrado.\n")
            return

        for item in resultados:
            md.write(f"## Repositório: {item['repo']}\n")
            md.write(f"- Arquivo: `{item['arquivo']}`\n\n")
            md.write("### Runtimes encontrados e análise:\n")

            if not item["runtimes"]:
                md.write("- Nenhum runtime encontrado neste arquivo.\n\n")
                continue

            for rt in item["runtimes"]:
                py_version = parse_python_version_tuple(rt)
                if py_version is None:
                    md.write(f"- Runtime: `{rt}` → Não aplicável para verificação de versão mínima (não é Python ou versão não interpretável)\n")
                else:
                    if py_version < VERSAO_RECOMENDADA_TUPLE:
                        md.write((
                            f"- Runtime: `{rt}` → Desatualizado — versão atual `{format_version_tuple(py_version)}` "
                            f"(mínimo recomendado: `{format_version_tuple(VERSAO_RECOMENDADA_TUPLE)}`)\n"
                        ))
                    else:
                        md.write(f"- Runtime: `{rt}` → Atual — versão `{format_version_tuple(py_version)}`\n")

            md.write("\n---\n\n")


def main():
    repos = listar_repos(USERNAME)

    if not repos:
        print("Nenhum repositório retornado. Verifique USERNAME e TOKEN.")
        return

    resultados: List[Dict] = []

    for repo in repos:
        nome = repo.get("name")
        if not nome:
            continue

        if FILTRO.lower() not in nome.lower():
            continue

        default_branch = repo.get("default_branch", "main")

        print("Analisando repositório:", nome, "- branch:", default_branch)

        arquivos = listar_arquivos(USERNAME, nome, default_branch)

        tf_files = [a["path"] for a in arquivos if a.get("path", "").endswith(".tf")]

        print("  Arquivos .tf encontrados:", len(tf_files))

        for tf in tf_files:
            conteudo = baixar_arquivo(USERNAME, nome, tf)
            if conteudo is None:
                continue

            runtimes = extrair_runtimes_do_conteudo(conteudo)

            resultados.append({
                "repo": nome,
                "arquivo": tf,
                "runtimes": runtimes
            })

    gerar_markdown(resultados, OUTPUT_FILE)
    print("Arquivo gerado:", OUTPUT_FILE)


if __name__ == "__main__":
    main()