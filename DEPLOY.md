# Deploy — Dourados Ambiental OS

Duas opções de hospedagem, para você comparar e decidir qual manter.
As duas usam o mesmo código (`app.py`), sem necessidade de branch
separada.

---

## 1. Railway (recomendado — com volume persistente)

### 1.1 Subir o código para o GitHub

Railway faz deploy a partir de um repositório GitHub.

```bash
cd dourados_ambiental_app
git init
git add .
git commit -m "Dourados Ambiental OS - versão inicial"
```

Crie um repositório novo no GitHub (ex.: `dourados-ambiental-os`) e depois:

```bash
git remote add origin https://github.com/SEU-USUARIO/dourados-ambiental-os.git
git branch -M main
git push -u origin main
```

### 1.2 Criar o projeto no Railway

1. Acesse [railway.app](https://railway.app) e faça login (pode usar a conta do GitHub)
2. **New Project** → **Deploy from GitHub repo** → selecione `dourados-ambiental-os`
3. Railway detecta o `Procfile` automaticamente e já sobe o app com gunicorn

### 1.3 Adicionar um Volume (para o banco não se perder a cada deploy)

Sem isso, toda vez que você atualizar o código o SQLite seria apagado.

1. No projeto, vá em **Settings** → **Volumes** → **New Volume**
2. Defina o **Mount Path** como `/data`
3. Salve — o Railway reinicia o serviço com o volume montado

### 1.4 Configurar variáveis de ambiente

Em **Variables**, adicione:

| Variável | Valor |
|---|---|
| `DATABASE_PATH` | `/data/dourados.db` |
| `SECRET_KEY` | uma string aleatória qualquer (ex. gere com `python -c "import secrets; print(secrets.token_hex(32))"`) |

O app já está preparado para ler essas duas variáveis (veja `app.py`).

### 1.5 Gerar o domínio público

Em **Settings** → **Networking** → **Generate Domain**. Você recebe uma
URL tipo `https://dourados-ambiental-os-production.up.railway.app` — é essa que
você acessa do celular, de qualquer rede.

### 1.6 Testar

Abra a URL gerada, cadastre um cliente e uma OS de teste. Depois force
um novo deploy (ex. um commit vazio) e confirme que a OS de teste
continua lá — isso confirma que o volume está funcionando.

---

## 2. PythonAnywhere (alternativa)

O disco no PythonAnywhere já é persistente por padrão (não precisa de
volume), mas o plano gratuito não permite gunicorn — eles usam seu
próprio servidor WSGI, o que já está previsto abaixo.

### 2.1 Enviar os arquivos

Envie a pasta `dourados_ambiental_app` inteira via **Files** (upload manual)
ou clonando o repositório GitHub direto no console Bash do
PythonAnywhere:

```bash
git clone https://github.com/SEU-USUARIO/dourados-ambiental-os.git
```

### 2.2 Criar o virtualenv e instalar dependências

No console Bash do PythonAnywhere:

```bash
cd dourados-ambiental-os
mkvirtualenv --python=/usr/bin/python3.10 dourados-venv
pip install -r requirements.txt
```

(gunicorn não é necessário aqui — pode deixar instalado mesmo, não atrapalha)

### 2.3 Configurar a Web App

1. Aba **Web** → **Add a new web app** → **Manual configuration** → Python 3.10
2. Em **Virtualenv**, aponte para `/home/SEU_USUARIO/.virtualenvs/dourados-venv`
3. Edite o arquivo **WSGI configuration file** (link na mesma página) e troque o conteúdo por:

```python
import sys
import os

path = '/home/SEU_USUARIO/dourados-ambiental-os'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DATABASE_PATH'] = '/home/SEU_USUARIO/dourados-ambiental-os/instance/dourados.db'
os.environ['SECRET_KEY'] = 'coloque-uma-chave-aleatoria-aqui'

from app import app as application
```

4. Clique em **Reload** na aba Web

### 2.4 Mapear a pasta `static` (logo, CSS, ícones)

No modo "Manual configuration", o PythonAnywhere não serve sozinho os
arquivos estáticos do Flask (`static/`) — sem esse passo, a página
carrega sem a logo e sem o CSS.

Na aba **Web**, seção **Static files**, adicione:

| URL | Directory |
|---|---|
| `/static/` | `/home/SEU_USUARIO/dourados-ambiental-os/static` |

Clique em **Reload** de novo depois de salvar.

### 2.5 Testar

Acesse `https://SEU_USUARIO.pythonanywhere.com` (URL mostrada no topo da aba Web).

---

## Qual escolher?

- **Railway**: domínio mais direto, deploy automático a cada `git push`, bom para evoluir o app rapidamente.
- **PythonAnywhere**: já é o que você usa para o outro sistema que você já utiliza, então mantém tudo no mesmo lugar/hábito; plano gratuito é mais limitado em CPU/tráfego.

Nada impede manter os dois rodando em paralelo durante os testes — os bancos de dados são independentes entre si.
