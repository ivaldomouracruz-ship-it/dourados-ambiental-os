# Sistema de Ordens de Serviço — Dourados Ambiental

Aplicativo web (Flask + SQLite) para emissão e controle de Ordens de
Serviço da Dourados Ambiental: numeração automática, cadastro de
clientes com histórico, assinatura digital (técnico e cliente) e
impressão/PDF no navegador.

## Rodando localmente

```bash
cd dourados_ambiental_app
pip install -r requirements.txt
python app.py
```

Acesse http://127.0.0.1:5000

Na primeira execução o banco `instance/dourados.db` é criado
automaticamente (schema em `schema.sql`).

## O que o sistema faz

- **Dashboard** — contagem de OS por status e clientes cadastrados.
- **Nova OS** — formulário com 8 seções: dados do cliente, período de
  execução, os 15 serviços da Dourados Ambiental (com descrição de
  escopo — controle de pragas urbanas, higienização de caixa d'água,
  desentupimento, hidrojateamento e sanitização de ambientes),
  observações, materiais/equipamentos, equipe (adicionar/remover
  colaboradores), checklist de vistoria e responsável técnico.
- **Numeração automática** — cada OS recebe um número no formato
  `DA-2026-0001`, sequencial.
- **Clientes** — cadastro com histórico completo de OS por cliente;
  ao criar uma OS você escolhe um cliente já cadastrado ou cria um
  novo na hora.
- **Visualizar / Imprimir** — página de detalhe da OS reproduz um
  layout formal (cabeçalho com a logo, seções, tabelas) e tem botão
  "Imprimir / Salvar PDF" que usa a impressão do navegador
  (Ctrl+P → Salvar como PDF).
- **Assinatura digital do cliente** — cada OS tem um link público
  único (`/assinar/<token>`), sem necessidade de login, que você
  envia pro cliente (WhatsApp, e-mail etc.). Nele, o cliente vê a OS
  completa (dados do cliente, período, serviços, materiais, equipe,
  checklist e a assinatura do responsável técnico da Dourados
  Ambiental), digita o nome completo e desenha a própria assinatura
  na tela (dedo ou mouse) — é exigido um traço mínimo real, não basta
  um toque rápido sem desenhar nada. Ao confirmar, a assinatura fica
  registrada permanentemente naquela OS — visível tanto na página
  pública (com aviso de "já assinado") quanto na visualização interna
  da OS, junto com data/hora. Útil para manter um arquivo de OS
  assinadas pelo cliente, por exemplo em condomínios, indústrias e
  redes de supermercados atendidas.
  Se por engano uma assinatura ficar incompleta/em branco, o
  responsável da Dourados Ambiental pode clicar em "Resetar
  assinatura do cliente" na visualização da OS — isso limpa a
  assinatura salva e libera o mesmo link para o cliente assinar de
  novo.
- **Assinatura digital do responsável técnico** — ao criar (ou editar)
  uma OS, o responsável técnico da Dourados Ambiental também desenha
  a própria assinatura num quadro (igual ao do cliente, com a mesma
  exigência de traço mínimo), além de informar o nome. Essa
  assinatura aparece tanto na visualização interna quanto na página
  pública que o cliente abre — ou seja, o cliente já vê que a OS foi
  assinada pela Dourados Ambiental antes de assinar a parte dele. Ao
  editar uma OS já assinada, a assinatura existente é exibida com a
  opção "Refazer assinatura" para desenhar uma nova, se necessário.

## Estrutura

```
app.py              — rotas e lógica
schema.sql          — schema do banco SQLite
templates/          — páginas HTML (Jinja2)
static/style.css     — estilos (paleta azul-marinho/dourado/verde da Dourados Ambiental)
static/img/logo.png  — logo da Dourados Ambiental
instance/            — banco de dados (criado automaticamente, git-ignored)
```

## Deploy

Guia passo a passo completo para Railway (com volume persistente) e
PythonAnywhere está em **[DEPLOY.md](DEPLOY.md)**.

Resumo do que já está pronto no código para produção:
- `Procfile` configurado para rodar com `gunicorn`
- `DATABASE_PATH` (variável de ambiente) permite apontar o banco para
  um volume persistente (Railway) ou caminho fixo (PythonAnywhere) —
  sem isso, usa `instance/dourados.db` local, como no desenvolvimento
- `SECRET_KEY` também vem de variável de ambiente
- O schema do banco (`schema.sql`) é aplicado automaticamente na
  inicialização, tanto em `python app.py` quanto sob gunicorn

## Pendências / próximos passos sugeridos

- Autenticação de usuários (login) caso o sistema seja usado por
  múltiplos colaboradores.
- Geração de PDF no servidor (ex. `weasyprint`) em vez de depender
  do "Imprimir" do navegador.
- Ajustar a lista de 15 serviços caso a Dourados Ambiental queira
  adicionar, remover ou renomear algum item do catálogo.
