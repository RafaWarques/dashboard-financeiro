from supabase import create_client, Client
import pandas as pd
import os

# 🔑 Pega as credenciais do ambiente (GitHub Secrets)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# ✔️ Conecta no Supabase
supabase: Client = create_client(url, key)

try:
    # 🔍 Faz a leitura da tabela 'despesas'
    res = supabase.table("despesas").select("*").execute()

    df = pd.DataFrame(res.data)

    print("✅ Dados encontrados na tabela 'despesas':")
    print(df)

    if df.empty:
        print("⚠️ A tabela está vazia ou não existem registros.")
    else:
        print(f"✔️ Número de registros encontrados: {len(df)}")

except Exception as e:
    print("❌ Erro ao conectar ou buscar dados do Supabase:")
    print(e)
    exit(1)
