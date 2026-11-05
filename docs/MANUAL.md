# Manual de Utilização — Eco Sand | Gestão de Treinamentos

## Acesso
Acesse a URL do sistema e informe usuário e senha. O usuário padrão inicial é `admin` com senha `admin123`. Recomenda-se alterar a senha após o primeiro acesso.

## Módulos

### Dashboard
Visão geral com indicadores, gráficos e lista de prioridades. Use os filtros (ano, mês, setor, cargo, situação) para refinar.

### Colaboradores
Cadastro, edição, inativação e consulta da ficha individual com todos os treinamentos.

### Setores / Cargos / Treinamentos
Cadastros auxiliares. O prazo de validade do treinamento (em dias) é opcional; se não definido, o status fica "Dados incompletos".

### Realizações
Registra treinamentos realizados e renovações. Cada renovação cria um novo registro histórico, preservando os anteriores. A data de vencimento é calculada automaticamente: data da realização + prazo em dias.

### Agenda
Visualização tabular dos vencimentos com filtros rápidos (7, 15, 30, 60, 90 dias).

### Relatórios
Geral por ano, por treinamento, por colaborador, por setor, mensal (calendário), anual e individual (impressão). Exportação em Excel e CSV.

### Pendências
Central de acompanhamento. Marcar como acompanhada não altera o status real do treinamento.

### Importação
Importa a planilha Excel original. Informe o caminho do arquivo no servidor e use Pré-visualizar antes de confirmar.

### Usuários
Gerenciamento de usuários e perfis (admin, RH, consulta).

### Auditoria
Histórico de alterações.

### Configurações
Janela de alerta (padrão 30 dias).

## Regras de status
- Vencido: data de vencimento < hoje.
- Próximo do vencimento: hoje <= vencimento < hoje + 30 dias.
- Em dia: vencimento >= hoje + 30 dias.
- Dados incompletos: falta data de realização ou prazo.
'''