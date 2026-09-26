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

- **Início:** cadastro rápido por voz, resumo do período e últimos lançamentos.
- **Fixas e assinaturas:** custo mensal ativo e desativação de cobranças recorrentes.
- **Análises:** indicadores, categorias, evolução mensal, maiores compras e recorrências.
- **Parcelas:** compromissos futuros e calendário das parcelas.
- **Planejamento:** tendências, insights personalizados e metas sugeridas por categoria.

Os filtros de responsável e período ficam na barra lateral. No celular, a navegação
principal permanece no topo e os filtros podem ficar recolhidos.
