# dashboard-financeiro
dashboard de controle financeiro familiar

## Cadastro de despesa por voz

O formulário aceita frases como:

> Comprei almoço por 42 reais no cartão.

O áudio é transcrito e interpretado para preencher categoria, descrição, valor,
parcelas e responsável. O usuário revisa os dados antes de salvar no Supabase.

Categorias disponíveis: Alimentação, Lazer, Higiene, Saúde, Transporte, Casa e Outros.

O gravador fica visível no topo da página, inclusive no celular, sem precisar abrir
uma seção de cadastro. A barra lateral inicia recolhida para aproveitar melhor a tela.

1. Instale as dependências com `pip install -r requirements.txt`.
2. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
3. Informe `OPENAI_API_KEY` no arquivo criado (ele é ignorado pelo Git).
4. Execute `streamlit run supabase_financeiro.py`.

## Despesas fixas e assinaturas

O cadastro da página **Início** permite escolher entre despesa comum, despesa fixa e
assinatura. Para habilitar as cobranças recorrentes:

1. Abra o SQL Editor do Supabase.
2. Execute `supabase/migrations/20260926170000_despesas_recorrentes.sql`.
3. Opcionalmente, execute `supabase/cron_recorrencias.sql` para processar as cobranças
   todos os dias, mesmo sem abrir o app.

Sem o agendamento opcional, o app sincroniza automaticamente as cobranças vencidas
sempre que é aberto. O processo é idempotente: cada regra gera no máximo um lançamento
por mês, inclusive se a sincronização for executada mais de uma vez.

## Estrutura do aplicativo

- **Início:** cadastro rápido por voz, resumo do mês e últimos lançamentos.
- **Visão mensal:** total mensal com parcelas e recorrências, categorias, composição e evolução.
- **Despesas:** tabela de despesas comuns com filtros por mês e categoria e totais consolidados.
- **Fixas e assinaturas:** tabelas de cobranças ativas, custo mensal e opção de desativação.
- **Parcelas:** compromissos futuros e calendário das parcelas.

O filtro de responsável fica na barra lateral. Os filtros de mês e categoria aparecem
nas páginas em que são necessários. No celular, a navegação principal permanece no
topo e a barra lateral pode ficar recolhida.
