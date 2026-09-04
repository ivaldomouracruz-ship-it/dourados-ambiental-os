-- Dourados Ambiental — Sistema de Ordens de Serviço
-- Schema SQLite

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_razao_social TEXT NOT NULL,
    cnpj_cpf TEXT,
    telefone TEXT,
    email TEXT,
    endereco TEXT,
    segmento TEXT,
    criado_em TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ordens_servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_os TEXT UNIQUE NOT NULL,
    data_emissao TEXT NOT NULL,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    contato_responsavel TEXT,
    data_inicio TEXT,
    data_conclusao TEXT,
    horario_inicio TEXT,
    horario_fim TEXT,
    periodicidade TEXT,
    servicos_json TEXT,          -- lista de códigos de serviço selecionados, ex: ["DA.01","DA.03"]
    produtos_json TEXT,          -- lista de códigos de produtos químicos utilizados, ex: ["PR.01","PR.04"]
    descricao_observacoes TEXT,
    materiais_equipamentos TEXT,
    equipe_json TEXT,            -- lista de {nome, funcao}
    checklist_json TEXT,         -- lista de itens marcados
    responsavel_tecnico TEXT,
    responsavel_tecnico_assinatura TEXT, -- assinatura do responsável técnico, desenhada, PNG em base64 (data URL)
    status TEXT DEFAULT 'Aberta', -- Aberta, Em andamento, Concluída, Cancelada
    token_assinatura TEXT,             -- token único usado no link público de assinatura do cliente
    assinatura_cliente_nome TEXT,      -- nome digitado pelo cliente ao assinar
    assinatura_cliente_imagem TEXT,    -- assinatura desenhada, salva como PNG em base64 (data URL)
    assinatura_cliente_data TEXT,      -- data/hora em que o cliente assinou
    criado_em TEXT DEFAULT (datetime('now', 'localtime')),
    atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_os_cliente ON ordens_servico(cliente_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON ordens_servico(status);
