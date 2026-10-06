# Lista de desejos — instalação e evolução

A página **♡ Lista de desejos** salva nome, valor estimado, descrição e uma foto
opcional. A foto pode vir da câmera do navegador ou da galeria/arquivo. Cada item
pertence a Rafael ou Nathalia e respeita o filtro de responsável na barra lateral.
Há edição, troca/remoção de foto, busca, ordenação, exclusão com confirmação e
histórico de itens comprados. O resumo mostra quantidade e valor dos desejos e
quantidade de conquistas.

## 1. Criar a estrutura no Supabase

1. Abra o **mesmo projeto Supabase** que contém a tabela `despesas`.
2. Entre em **SQL Editor → New query**.
3. Cole todo o conteúdo de
   [`20261006120000_wishlist.sql`](../supabase/migrations/20261006120000_wishlist.sql).
4. Clique em **Run**. O script usa uma transação e pode ser executado novamente.
5. Em **Table Editor**, confira a tabela `public.wishlist_itens`.
6. Em **Storage**, confira o bucket `wishlist-fotos`, marcado como **Private**.

Não é necessário alterar `despesas`, `despesas_recorrentes` nem os agendamentos.
O SQL também cria as validações, os índices e a atualização automática de
`atualizado_em`. Não crie políticas públicas para esta tabela ou para esse bucket.

## 2. Configurar a chave de servidor

Como o app atual não possui login, a wishlist usa um cliente Supabase exclusivo
no servidor Streamlit. A migração bloqueia leitura/escrita da nova tabela pelas
chaves `anon` e pelas sessões `authenticated`; o servidor usa `service_role`.

No Supabase, abra **Settings → API Keys** (ou o diálogo **Connect → API Keys**).
Copie uma **Secret API key** (`sb_secret_...`) ou, em **Legacy API Keys**, a chave
**service_role**. Adicione ao `.streamlit/secrets.toml` existente, preservando as
outras configurações:

```toml
SUPABASE_WISHLIST_KEY = "sua-chave-de-servidor-do-mesmo-projeto"
```

No Streamlit Community Cloud, coloque o mesmo valor em **App settings → Secrets**
e reinicie o app. Em outro servidor, a variável de ambiente
`SUPABASE_WISHLIST_KEY` também funciona e tem precedência sobre os secrets.

Essa chave tem privilégios administrativos no projeto: mantenha-a exclusivamente
nos secrets do servidor. Não a coloque em código, Git, links, componentes HTML ou
no campo `SUPABASE_ANON_KEY`. O arquivo local de secrets já é ignorado pelo Git.
O cliente das despesas continua usando a configuração atual.

As imagens são acessadas com URLs assinadas que expiram em uma hora. O bucket
privado impede acesso por URL pública; a chave de servidor pode gerar essas URLs.
**Quem tem acesso ao aplicativo continua podendo acessar a lista compartilhada.**
O filtro por Rafael/Nathalia serve para organizar, não autentica usuários. Para
acesso individual, será necessário adicionar Supabase Auth e políticas por usuário
ou família antes de oferecer o aplicativo a outras pessoas.

Referências oficiais: [chaves de API](https://supabase.com/docs/guides/getting-started/api-keys),
[buckets](https://supabase.com/docs/guides/storage/buckets/creating-buckets) e
[URLs assinadas](https://supabase.com/docs/reference/python/storage-from-createsignedurl).

## 3. Atualizar e testar o aplicativo

```powershell
python -m pip install -r requirements.txt
python -m streamlit run supabase_financeiro.py
```

1. Abra **♡ Lista de desejos → ＋ Novo desejo**.
2. Informe nome, preço maior que zero, responsável e descrição opcional.
3. Escolha **Sem foto**, **Tirar foto** ou **Enviar imagem** e salve.
4. Recarregue a página para conferir a persistência.
5. Edite preço/descrição, troque a foto e confira os filtros.
6. Marque como comprado e use **Mostrar → Comprados**; é possível voltar o item
   para a lista de desejos.

Marcar como comprado **não gera despesa**. Registre a compra em **Início** para
que ela seja contabilizada. O valor da wishlist é uma estimativa, não uma reserva
de dinheiro ou um compromisso financeiro.

A câmera requer autorização do navegador e HTTPS no aplicativo publicado
(`localhost` funciona no desenvolvimento). Se o dispositivo não permitir usar a
câmera, envie uma foto da galeria. O widget utilizado é
[`st.camera_input`](https://docs.streamlit.io/develop/api-reference/widgets/st.camera_input).

## Estrutura e manutenção

| Campo | Função |
| --- | --- |
| `id` | UUID estável para futuras metas e vínculos |
| `nome`, `valor`, `descricao` | Dados do desejo; valor decimal com duas casas |
| `responsavel` | Rafael ou Nathalia |
| `status`, `comprado_em` | Desejado ou comprado, com data da conquista |
| `foto_path` | Caminho no Storage; não guarda uma URL temporária |
| `criado_em`, `atualizado_em` | Histórico de criação e última alteração |

Cada foto é salva em `wishlist-fotos/<id-do-item>/<id-da-foto>.jpg`. Entradas JPG,
PNG e WebP têm limite de 5 MB e 25 megapixels. O app corrige a orientação, reduz
para até 1.600 pixels por lado, converte para JPEG e remove metadados EXIF, incluindo
GPS. Fotos HEIC devem ser exportadas como JPG antes de enviar.

Na edição, uma nova foto é enviada antes de atualizar o item; a antiga só é removida
após a atualização. Na exclusão, o item é removido antes da foto. Banco e Storage
não compartilham uma transação: se a limpeza da imagem falhar, o app informa o
caminho para remoção manual em **Storage → wishlist-fotos**. Se você excluir linhas
diretamente pelo Table Editor, remova também as respectivas fotos pelo Storage.
Não apague registros da tabela interna `storage.objects` por SQL: use o Storage.

Erros de gravação preservam os campos para nova tentativa. Uma foto indisponível
não impede consultar ou editar o item. Sem chave ou migração, a página explica a
configuração pendente e as páginas financeiras continuam funcionando.

## Caminho para as recomendações financeiras

Esta entrega mantém a lista e sua persistência. As sugestões inteligentes ficam
para uma próxima etapa, com os seguintes critérios:

1. **Metas:** criar `wishlist_metas`, vinculada ao UUID do item, com prioridade,
   prazo e orçamento desejado. Registrar aportes em uma tabela separada para
   distinguir dinheiro realmente reservado de uma redução de gastos.
2. **Comparação confiável:** usar meses completos ou comparar até o mesmo dia;
   distribuir parcelas e incluir recorrências. Uma redução de gastos sozinha não
   prova saldo disponível. Incorporar renda, reserva de emergência e obrigações
   futuras antes de recomendar uma compra.
3. **Sugestões calculadas:** com saldo disponível confirmado de X, selecionar
   desejos que cabem no orçamento ou calcular prazo de uma meta com aporte mensal.
   Exibir período, valores usados e motivo da sugestão.
4. **Dicas e IA:** detectar categorias com aumento e simular uma redução escolhida
   pelo usuário. A IA pode explicar os cálculos em linguagem simples; saldo, prazo
   e limites devem vir das regras e dos dados, com revisão do usuário.

Assim, o UUID, os preços decimais, os responsáveis e o histórico de status desta
versão podem ser aproveitados sem misturar os desejos aos gastos efetivos.

## Verificação automatizada local

```powershell
python -m unittest discover -s tests -v
```

Os testes usam Supabase simulado e não alteram o projeto remoto.
