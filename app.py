import os
import json
import sqlite3
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Em produção (Railway), defina DATABASE_PATH apontando para o volume
# persistente montado (ex.: /data/dourados.db). Sem essa variável, usa
# o caminho local de desenvolvimento.
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "instance", "dourados.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-troque-em-producao")

# ---------------------------------------------------------------------------
# Serviços fixos oferecidos pela Dourados Ambiental
# ---------------------------------------------------------------------------
SERVICOS = [
    {"codigo": "DA.01", "nome": "Desinsetização",
     "descricao": "Eliminação e controle de insetos rasteiros e voadores em geral, com aplicação de produto residual e/ou UBV."},
    {"codigo": "DA.02", "nome": "Desratização",
     "descricao": "Controle e eliminação de roedores, com uso de iscas, armadilhas e barreiras físicas."},
    {"codigo": "DA.03", "nome": "Controle de Cupins",
     "descricao": "Tratamento preventivo e curativo contra cupins de solo e de madeira, protegendo estruturas e mobiliário."},
    {"codigo": "DA.04", "nome": "Controle de Formigas",
     "descricao": "Tratamento de formigueiros e trilhas com iscas e produtos específicos para eliminação da colônia."},
    {"codigo": "DA.05", "nome": "Controle de Baratas",
     "descricao": "Aplicação de gel, pó e produtos residuais para eliminação de baratas em ambientes residenciais e comerciais."},
    {"codigo": "DA.06", "nome": "Controle de Escorpiões",
     "descricao": "Identificação dos pontos de infestação e aplicação de produtos específicos para eliminação e prevenção."},
    {"codigo": "DA.07", "nome": "Controle de Aranhas",
     "descricao": "Localização de focos e aplicação de produtos residuais para eliminação e prevenção de novas infestações."},
    {"codigo": "DA.08", "nome": "Controle de Mosquitos e Moscas",
     "descricao": "Aplicação de larvicidas e adulticidas para controle de mosquitos e moscas, incluindo vetores de doenças."},
    {"codigo": "DA.09", "nome": "Controle de Pulgas e Carrapatos",
     "descricao": "Tratamento de ambientes internos, externos e áreas de estimação para eliminação de pulgas e carrapatos."},
    {"codigo": "DA.10", "nome": "Controle de Percevejos",
     "descricao": "Inspeção detalhada e tratamento específico para eliminação de percevejos de cama e do ambiente."},
    {"codigo": "DA.11", "nome": "Controle de Pombos e Morcegos",
     "descricao": "Instalação de barreiras físicas e manejo para afastamento de pombos e morcegos, conforme legislação vigente."},
    {"codigo": "DA.12", "nome": "Higienização de Caixa d'Água",
     "descricao": "Limpeza completa, desinfecção e impermeabilização de reservatórios, com inspeção técnica e relatório fotográfico."},
    {"codigo": "DA.13", "nome": "Desentupimento",
     "descricao": "Desobstrução de pias, vasos sanitários, ralos, colunas, redes de esgoto, redes pluviais, caixas de gordura e fossas."},
    {"codigo": "DA.14", "nome": "Hidrojateamento",
     "descricao": "Limpeza de tubulações e superfícies com jato de água de alta pressão, removendo gordura, lodo e incrustações."},
    {"codigo": "DA.15", "nome": "Sanitização de Ambientes",
     "descricao": "Higienização e desinfecção de ambientes com produtos sanitizantes para eliminação de vírus, bactérias e fungos."},
]
SERVICOS_POR_CODIGO = {s["codigo"]: s for s in SERVICOS}

CHECKLIST_ITENS = [
    "Ambiente vistoriado antes do início dos trabalhos",
    "Serviços executados conforme escopo definido",
    "Equipamentos de Proteção Individual (EPIs) utilizados",
    "Área isolada/sinalizada durante a aplicação, quando aplicável",
    "Cliente orientado sobre cuidados e prazo de reentrada no ambiente",
    "Área limpa e organizada após execução",
    "Vistoria final realizada com o cliente",
]

STATUS_OPCOES = ["Aberta", "Em andamento", "Concluída", "Cancelada"]


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE_DIR, "schema.sql"), "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
    db.close()


def migrar_schema():
    """Adiciona colunas novas em bancos já existentes, sem apagar dados.
    Roda a cada início do app; verifica antes de alterar (idempotente)."""
    db = sqlite3.connect(DB_PATH)
    colunas_existentes = {row[1] for row in db.execute("PRAGMA table_info(ordens_servico)").fetchall()}
    colunas_novas = {
        "token_assinatura": "TEXT",
        "assinatura_cliente_nome": "TEXT",
        "assinatura_cliente_imagem": "TEXT",
        "assinatura_cliente_data": "TEXT",
        "responsavel_tecnico_assinatura": "TEXT",
    }
    for coluna, tipo in colunas_novas.items():
        if coluna not in colunas_existentes:
            db.execute(f"ALTER TABLE ordens_servico ADD COLUMN {coluna} {tipo}")
    db.commit()
    db.close()


def gerar_token_assinatura():
    return secrets.token_urlsafe(24)


# Garante que o schema exista tanto rodando com `python app.py` (dev)
# quanto sob gunicorn em produção (Railway/PythonAnywhere), onde este
# bloco `if __name__` nunca é executado — o import do módulo já cria
# o banco/tabelas se ainda não existirem (CREATE TABLE IF NOT EXISTS).
init_db()
migrar_schema()


def gerar_numero_os(db):
    row = db.execute("SELECT numero_os FROM ordens_servico ORDER BY id DESC LIMIT 1").fetchone()
    if row and row["numero_os"]:
        try:
            seq = int(row["numero_os"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = db.execute("SELECT COUNT(*) c FROM ordens_servico").fetchone()["c"] + 1
    else:
        seq = 1
    ano = datetime.now().year
    return f"DA-{ano}-{seq:04d}"


# ---------------------------------------------------------------------------
# Rotas — Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    db = get_db()
    total_os = db.execute("SELECT COUNT(*) c FROM ordens_servico").fetchone()["c"]
    abertas = db.execute("SELECT COUNT(*) c FROM ordens_servico WHERE status='Aberta'").fetchone()["c"]
    andamento = db.execute("SELECT COUNT(*) c FROM ordens_servico WHERE status='Em andamento'").fetchone()["c"]
    concluidas = db.execute("SELECT COUNT(*) c FROM ordens_servico WHERE status='Concluída'").fetchone()["c"]
    total_clientes = db.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"]
    recentes = db.execute("""
        SELECT os.*, c.nome_razao_social
        FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
        ORDER BY os.id DESC LIMIT 8
    """).fetchall()
    return render_template(
        "dashboard.html",
        total_os=total_os, abertas=abertas, andamento=andamento,
        concluidas=concluidas, total_clientes=total_clientes, recentes=recentes,
    )


# ---------------------------------------------------------------------------
# Rotas — Ordens de Serviço
# ---------------------------------------------------------------------------
@app.route("/os")
def listar_os():
    db = get_db()
    status_filtro = request.args.get("status", "")
    busca = request.args.get("q", "").strip()

    query = """
        SELECT os.*, c.nome_razao_social
        FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
        WHERE 1=1
    """
    params = []
    if status_filtro:
        query += " AND os.status = ?"
        params.append(status_filtro)
    if busca:
        query += " AND (os.numero_os LIKE ? OR c.nome_razao_social LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])
    query += " ORDER BY os.id DESC"

    ordens = db.execute(query, params).fetchall()
    return render_template(
        "os_lista.html", ordens=ordens, status_opcoes=STATUS_OPCOES,
        status_filtro=status_filtro, busca=busca,
    )


@app.route("/os/novo", methods=["GET", "POST"])
def nova_os():
    db = get_db()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")

        if cliente_id == "novo":
            nome = request.form.get("novo_cliente_nome", "").strip()
            if not nome:
                flash("Informe o nome/razão social do novo cliente.", "erro")
                return redirect(url_for("nova_os"))
            cur = db.execute(
                """INSERT INTO clientes (nome_razao_social, cnpj_cpf, telefone, email, endereco, segmento)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nome,
                 request.form.get("novo_cliente_cnpj_cpf", "").strip(),
                 request.form.get("novo_cliente_telefone", "").strip(),
                 request.form.get("novo_cliente_email", "").strip(),
                 request.form.get("novo_cliente_endereco", "").strip(),
                 request.form.get("novo_cliente_segmento", "").strip()),
            )
            cliente_id = cur.lastrowid
        else:
            if not cliente_id:
                flash("Selecione um cliente.", "erro")
                return redirect(url_for("nova_os"))
            cliente_id = int(cliente_id)

        servicos_selecionados = request.form.getlist("servicos")
        nomes_equipe = request.form.getlist("equipe_nome")
        funcoes_equipe = request.form.getlist("equipe_funcao")
        equipe = [
            {"nome": n.strip(), "funcao": f.strip()}
            for n, f in zip(nomes_equipe, funcoes_equipe) if n.strip()
        ]
        checklist_marcados = request.form.getlist("checklist")

        numero_os = gerar_numero_os(db)
        token_assinatura = gerar_token_assinatura()
        responsavel_assinatura = request.form.get("responsavel_assinatura_dataurl", "").strip()
        if not responsavel_assinatura.startswith("data:image"):
            responsavel_assinatura = None

        db.execute(
            """INSERT INTO ordens_servico (
                numero_os, data_emissao, cliente_id, contato_responsavel,
                data_inicio, data_conclusao, horario_inicio, horario_fim, periodicidade,
                servicos_json, descricao_observacoes, materiais_equipamentos,
                equipe_json, checklist_json, responsavel_tecnico, responsavel_tecnico_assinatura,
                status, token_assinatura
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                numero_os,
                request.form.get("data_emissao") or datetime.now().strftime("%Y-%m-%d"),
                cliente_id,
                request.form.get("contato_responsavel", "").strip(),
                request.form.get("data_inicio", ""),
                request.form.get("data_conclusao", ""),
                request.form.get("horario_inicio", ""),
                request.form.get("horario_fim", ""),
                request.form.get("periodicidade", ""),
                json.dumps(servicos_selecionados, ensure_ascii=False),
                request.form.get("descricao_observacoes", "").strip(),
                request.form.get("materiais_equipamentos", "").strip(),
                json.dumps(equipe, ensure_ascii=False),
                json.dumps(checklist_marcados, ensure_ascii=False),
                request.form.get("responsavel_tecnico", "").strip(),
                responsavel_assinatura,
                request.form.get("status", "Aberta"),
                token_assinatura,
            ),
        )
        db.commit()
        flash(f"Ordem de Serviço {numero_os} criada com sucesso.", "sucesso")
        cur = db.execute("SELECT id FROM ordens_servico WHERE numero_os = ?", (numero_os,)).fetchone()
        return redirect(url_for("ver_os", os_id=cur["id"]))

    clientes = db.execute("SELECT * FROM clientes ORDER BY nome_razao_social").fetchall()
    numero_previsto = gerar_numero_os(db)
    return render_template(
        "os_form.html", clientes=clientes, servicos=SERVICOS,
        checklist_itens=CHECKLIST_ITENS, status_opcoes=STATUS_OPCOES,
        numero_previsto=numero_previsto, ordem=None,
        equipe=[], servicos_marcados=[], checklist_marcados=[],
        hoje=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/os/<int:os_id>/editar", methods=["GET", "POST"])
def editar_os(os_id):
    db = get_db()
    ordem = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    if ordem is None:
        abort(404)

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        if cliente_id == "novo":
            nome = request.form.get("novo_cliente_nome", "").strip()
            if not nome:
                flash("Informe o nome/razão social do novo cliente.", "erro")
                return redirect(url_for("editar_os", os_id=os_id))
            cur = db.execute(
                """INSERT INTO clientes (nome_razao_social, cnpj_cpf, telefone, email, endereco, segmento)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nome,
                 request.form.get("novo_cliente_cnpj_cpf", "").strip(),
                 request.form.get("novo_cliente_telefone", "").strip(),
                 request.form.get("novo_cliente_email", "").strip(),
                 request.form.get("novo_cliente_endereco", "").strip(),
                 request.form.get("novo_cliente_segmento", "").strip()),
            )
            cliente_id = cur.lastrowid
        else:
            cliente_id = int(cliente_id)

        servicos_selecionados = request.form.getlist("servicos")
        nomes_equipe = request.form.getlist("equipe_nome")
        funcoes_equipe = request.form.getlist("equipe_funcao")
        equipe = [
            {"nome": n.strip(), "funcao": f.strip()}
            for n, f in zip(nomes_equipe, funcoes_equipe) if n.strip()
        ]
        checklist_marcados = request.form.getlist("checklist")

        responsavel_assinatura = request.form.get("responsavel_assinatura_dataurl", "").strip()
        if not responsavel_assinatura.startswith("data:image"):
            responsavel_assinatura = None

        db.execute(
            """UPDATE ordens_servico SET
                data_emissao=?, cliente_id=?, contato_responsavel=?,
                data_inicio=?, data_conclusao=?, horario_inicio=?, horario_fim=?, periodicidade=?,
                servicos_json=?, descricao_observacoes=?, materiais_equipamentos=?,
                equipe_json=?, checklist_json=?, responsavel_tecnico=?, responsavel_tecnico_assinatura=?,
                status=?, atualizado_em=datetime('now','localtime')
               WHERE id=?""",
            (
                request.form.get("data_emissao"),
                cliente_id,
                request.form.get("contato_responsavel", "").strip(),
                request.form.get("data_inicio", ""),
                request.form.get("data_conclusao", ""),
                request.form.get("horario_inicio", ""),
                request.form.get("horario_fim", ""),
                request.form.get("periodicidade", ""),
                json.dumps(servicos_selecionados, ensure_ascii=False),
                request.form.get("descricao_observacoes", "").strip(),
                request.form.get("materiais_equipamentos", "").strip(),
                json.dumps(equipe, ensure_ascii=False),
                json.dumps(checklist_marcados, ensure_ascii=False),
                request.form.get("responsavel_tecnico", "").strip(),
                responsavel_assinatura,
                request.form.get("status", "Aberta"),
                os_id,
            ),
        )
        db.commit()
        flash(f"Ordem de Serviço {ordem['numero_os']} atualizada.", "sucesso")
        return redirect(url_for("ver_os", os_id=os_id))

    clientes = db.execute("SELECT * FROM clientes ORDER BY nome_razao_social").fetchall()
    return render_template(
        "os_form.html", clientes=clientes, servicos=SERVICOS,
        checklist_itens=CHECKLIST_ITENS, status_opcoes=STATUS_OPCOES,
        numero_previsto=ordem["numero_os"], ordem=ordem,
        equipe=json.loads(ordem["equipe_json"] or "[]"),
        servicos_marcados=json.loads(ordem["servicos_json"] or "[]"),
        checklist_marcados=json.loads(ordem["checklist_json"] or "[]"),
        hoje=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/os/<int:os_id>")
def ver_os(os_id):
    db = get_db()
    ordem = db.execute(
        """SELECT os.*, c.nome_razao_social, c.cnpj_cpf, c.telefone, c.email, c.endereco, c.segmento
           FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
           WHERE os.id = ?""", (os_id,)
    ).fetchone()
    if ordem is None:
        abort(404)

    # OS criadas antes desta funcionalidade podem não ter token ainda — gera na hora
    if not ordem["token_assinatura"]:
        novo_token = gerar_token_assinatura()
        db.execute("UPDATE ordens_servico SET token_assinatura=? WHERE id=?", (novo_token, os_id))
        db.commit()
        ordem = db.execute(
            """SELECT os.*, c.nome_razao_social, c.cnpj_cpf, c.telefone, c.email, c.endereco, c.segmento
               FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
               WHERE os.id = ?""", (os_id,)
        ).fetchone()

    servicos_marcados = json.loads(ordem["servicos_json"] or "[]")
    servicos_detalhados = [SERVICOS_POR_CODIGO[c] for c in servicos_marcados if c in SERVICOS_POR_CODIGO]
    equipe = json.loads(ordem["equipe_json"] or "[]")
    checklist_marcados = set(json.loads(ordem["checklist_json"] or "[]"))
    link_assinatura = request.host_url.rstrip("/") + url_for("assinar_get", token=ordem["token_assinatura"])

    return render_template(
        "os_view.html", ordem=ordem, servicos_detalhados=servicos_detalhados,
        equipe=equipe, checklist_itens=CHECKLIST_ITENS,
        checklist_marcados=checklist_marcados, link_assinatura=link_assinatura,
    )


@app.route("/os/<int:os_id>/resetar-assinatura-cliente", methods=["POST"])
def resetar_assinatura_cliente(os_id):
    db = get_db()
    ordem = db.execute("SELECT numero_os FROM ordens_servico WHERE id=?", (os_id,)).fetchone()
    if ordem is None:
        abort(404)
    db.execute(
        """UPDATE ordens_servico SET
            assinatura_cliente_nome = NULL,
            assinatura_cliente_imagem = NULL,
            assinatura_cliente_data = NULL
           WHERE id = ?""",
        (os_id,),
    )
    db.commit()
    flash(
        f"Assinatura do cliente na OS {ordem['numero_os']} foi reiniciada. "
        "O mesmo link já pode ser usado para ele assinar novamente.",
        "sucesso",
    )
    return redirect(url_for("ver_os", os_id=os_id))


@app.route("/os/<int:os_id>/excluir", methods=["POST"])
def excluir_os(os_id):
    db = get_db()
    ordem = db.execute("SELECT numero_os FROM ordens_servico WHERE id=?", (os_id,)).fetchone()
    if ordem is None:
        abort(404)
    db.execute("DELETE FROM ordens_servico WHERE id=?", (os_id,))
    db.commit()
    flash(f"Ordem de Serviço {ordem['numero_os']} excluída.", "sucesso")
    return redirect(url_for("listar_os"))


# ---------------------------------------------------------------------------
# Rota pública — assinatura do cliente (sem login, acessada via link enviado)
# ---------------------------------------------------------------------------
@app.route("/assinar/<token>", methods=["GET"])
def assinar_get(token):
    db = get_db()
    ordem = db.execute(
        """SELECT os.*, c.nome_razao_social, c.cnpj_cpf, c.telefone, c.endereco
           FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
           WHERE os.token_assinatura = ?""", (token,)
    ).fetchone()
    if ordem is None:
        abort(404)

    servicos_marcados = json.loads(ordem["servicos_json"] or "[]")
    servicos_detalhados = [SERVICOS_POR_CODIGO[c] for c in servicos_marcados if c in SERVICOS_POR_CODIGO]
    equipe = json.loads(ordem["equipe_json"] or "[]")
    checklist_marcados = set(json.loads(ordem["checklist_json"] or "[]"))

    return render_template(
        "assinar_publico.html", ordem=ordem, servicos_detalhados=servicos_detalhados,
        equipe=equipe, checklist_itens=CHECKLIST_ITENS, checklist_marcados=checklist_marcados,
    )


@app.route("/assinar/<token>", methods=["POST"])
def assinar_post(token):
    db = get_db()
    ordem = db.execute("SELECT * FROM ordens_servico WHERE token_assinatura = ?", (token,)).fetchone()
    if ordem is None:
        abort(404)

    if ordem["assinatura_cliente_data"]:
        # já assinado anteriormente — não permite sobrescrever
        return redirect(url_for("assinar_get", token=token))

    nome = request.form.get("nome_confirmacao", "").strip()
    assinatura_dataurl = request.form.get("assinatura_dataurl", "")
    tem_assinatura = request.form.get("tem_assinatura") == "sim"
    try:
        comprimento_tracado = float(request.form.get("comprimento_tracado", "0"))
    except ValueError:
        comprimento_tracado = 0

    if (not nome or not tem_assinatura or not assinatura_dataurl.startswith("data:image")
            or comprimento_tracado < 15):
        flash("Preencha seu nome e desenhe a assinatura no quadro antes de confirmar.", "erro")
        return redirect(url_for("assinar_get", token=token))

    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    db.execute(
        """UPDATE ordens_servico SET
            assinatura_cliente_nome = ?, assinatura_cliente_imagem = ?, assinatura_cliente_data = ?
           WHERE id = ?""",
        (nome, assinatura_dataurl, agora, ordem["id"]),
    )
    db.commit()
    return redirect(url_for("assinar_get", token=token))


# ---------------------------------------------------------------------------
# Rotas — Clientes
# ---------------------------------------------------------------------------
@app.route("/clientes")
def listar_clientes():
    db = get_db()
    busca = request.args.get("q", "").strip()
    query = "SELECT * FROM clientes WHERE 1=1"
    params = []
    if busca:
        query += " AND (nome_razao_social LIKE ? OR cnpj_cpf LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])
    query += " ORDER BY nome_razao_social"
    clientes = db.execute(query, params).fetchall()

    contagem = {
        row["cliente_id"]: row["c"]
        for row in db.execute(
            "SELECT cliente_id, COUNT(*) c FROM ordens_servico GROUP BY cliente_id"
        ).fetchall()
    }
    return render_template("clientes_lista.html", clientes=clientes, busca=busca, contagem=contagem)


@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome_razao_social", "").strip()
        if not nome:
            flash("Informe o nome/razão social.", "erro")
            return redirect(url_for("novo_cliente"))
        db.execute(
            """INSERT INTO clientes (nome_razao_social, cnpj_cpf, telefone, email, endereco, segmento)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome,
             request.form.get("cnpj_cpf", "").strip(),
             request.form.get("telefone", "").strip(),
             request.form.get("email", "").strip(),
             request.form.get("endereco", "").strip(),
             request.form.get("segmento", "").strip()),
        )
        db.commit()
        flash("Cliente cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_clientes"))
    return render_template("cliente_form.html", cliente=None)


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    db = get_db()
    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    if cliente is None:
        abort(404)
    if request.method == "POST":
        db.execute(
            """UPDATE clientes SET nome_razao_social=?, cnpj_cpf=?, telefone=?, email=?, endereco=?, segmento=?
               WHERE id=?""",
            (request.form.get("nome_razao_social", "").strip(),
             request.form.get("cnpj_cpf", "").strip(),
             request.form.get("telefone", "").strip(),
             request.form.get("email", "").strip(),
             request.form.get("endereco", "").strip(),
             request.form.get("segmento", "").strip(),
             cliente_id),
        )
        db.commit()
        flash("Cliente atualizado.", "sucesso")
        return redirect(url_for("listar_clientes"))
    return render_template("cliente_form.html", cliente=cliente)


@app.route("/clientes/<int:cliente_id>/historico")
def historico_cliente(cliente_id):
    db = get_db()
    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    if cliente is None:
        abort(404)
    ordens = db.execute(
        "SELECT * FROM ordens_servico WHERE cliente_id=? ORDER BY id DESC", (cliente_id,)
    ).fetchall()
    return render_template("cliente_historico.html", cliente=cliente, ordens=ordens)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
