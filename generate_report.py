import requests
import base64
import re
from datetime import datetime

# === CONFIGURAÇÕES ===
USERNAME = "gustavorsilva"          # usuário ou org do GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # opcional: GitHub token pessoal (para evitar limite)
FILTRO = "lambda"                 # palavra a filtrar nos repositórios
OUTPUT_FILE = "output.md"         # nome do arquivo Markdown de saída

# === FUNÇÕES AUXILIARES ===

def github_request(url):
    """Faz requisições autenticadas à API do GitHub."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def decode_base64(content):
    """Decodifica conteúdo base64 de arquivos no GitHub."""
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extrair_runtime_terraform(conteudo):
    """
    Procura por runtimes Python no arquivo main.tf.
    Exemplo: runtime = "python3.9"
    """
    matches = re.findall(r'runtime\s*=\s*["\']python([\d\.]+)["\']', conteudo, re.IGNORECASE)
    if matches:
        version = matches[0]
        return ("Python", version)
    return ("Desconhecido", "-")


def precisa_atualizar(runtime):
    """
    Retorna True se o runtime for Python e a versão < 3.10
    """
    name, version = runtime
    if name == "Python":
        try:
            major, minor = version.split(".")
            version_tuple = (int(major), int(minor))
            return version_tuple < (3, 10)
        except Exception:
            return False
    return False


def get_runtime_from_terraform(repo_name):
    """Busca o arquivo main.tf e detecta a runtime."""
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents/main.tf"
    try:
        data = github_request(url)
        if "content" in data:
            decoded = decode_base64(data["content"])
            return extrair_runtime_terraform(decoded)
    except requests.HTTPError:
        pass
    return ("Desconhecido", "-")


# === PROGRAMA PRINCIPAL ===

def main():
    print(f"🔍 Buscando repositórios de {USERNAME} contendo '{FILTRO}'...\n")

    repos = github_request(f"https://api.github.com/users/{USERNAME}/repos?per_page=100")
    filtrados = [r for r in repos if FILTRO.lower() in r["name"].lower()]

    md = []
    md.append(f"# Relatório de Lambdas e runtimes detectadas 🚀\n")
    md.append(f"**Organização:** `{USERNAME}`  \n")
    md.append(f"**Total encontrado:** {len(filtrados)} repositório(s)\n")
    md.append("---\n")

    if not filtrados:
        md.append("Nenhum repositório encontrado.\n")
    else:
        for repo in filtrados:
            name = repo["name"]
            desc = repo["description"] or "Sem descrição"
            url = repo["html_url"]
            updated = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y")

            print(f"→ Verificando {name} ...")
            runtime = get_runtime_from_terraform(name)
            precisa = precisa_atualizar(runtime)

            md.append(f"## [{name}]({url})\n")
            md.append(f"📜 **Descrição:** {desc}\n\n")
            md.append(f"📦 **Runtime detectada:** `{runtime[0]} {runtime[1]}`  \n")
            md.append(f"📅 **Última atualização:** {updated}\n")

            if precisa:
                md.append(f"> ⚠️ **Atenção:** Atualize para Python 3.10 ou superior.\n")

            md.append("\n---\n")

    # Grava o resultado em Markdown
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\n✅ Relatório gerado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
