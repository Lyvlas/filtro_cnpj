from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from typing import Optional

app = FastAPI()

# Libera CORS para acesso via navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["local"]
colecao_cnpjs = db["filtro_cnpj"]
colecao_municipios = db["municipio"]
colecao_cnaes = db["cnaes"]
colecao_empresas = db["empresa"]

# Índices para melhorar performance
colecao_cnpjs.create_index([("uf", 1), ("codigo_municipio", 1), ("cnae_fiscal_principal", 1)])
colecao_empresas.create_index("cnpj_basico")

# Formatação do CNPJ completo
def formatar_cnpj(basico, ordem, dv):
    cnpj = f"{basico.zfill(8)}{ordem.zfill(4)}{dv.zfill(2)}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

# Endpoint principal de filtro
@app.get("/filtro")
def filtrar(uf: str, municipio: str, cnae: str,situacao: Optional[str] = None, page: int = Query(1, ge=1)):
    municipio = municipio.zfill(4)
    skip = (page - 1) * 100

    match_query = {
        "uf": uf.upper(),
        "codigo_municipio": municipio,
        "cnae_fiscal_principal": cnae
    }

    if situacao:
        match_query["situacao_cadastral"] = situacao

    pipeline = [
        {"$match": match_query},
        {"$sort": {"cnpj_basico": 1}},
        {"$skip": skip},
        {"$limit": 100},
        {"$lookup": {
            "from": "empresa",
            "localField": "cnpj_basico",
            "foreignField": "cnpj_basico",
            "as": "empresa_info"
        }},
        {"$unwind": {
            "path": "$empresa_info",
            "preserveNullAndEmptyArrays": True
        }},
        {"$project": {
            "_id": 0,
            "cnpj_basico": 1,
            "cnpj_ordem": 1,
            "cnpj_dv": 1,
            "matriz_filial": 1,
            "situacao_cadastral": 1,
            "ddd1": {"$ifNull": ["$ddd1", ""]},
            "telefone1": {"$ifNull": ["$telefone1", ""]},
            "email": {"$ifNull": ["$email", "—"]}, 
            "razao_social": {"$ifNull": ["$empresa_info.razao_social", "Desconhecida"]},
            "capital_social": {"$ifNull": ["$empresa_info.capital_social", 0]}
        }}

    ]

    resultados = list(colecao_cnpjs.aggregate(pipeline))

    total = colecao_cnpjs.count_documents(match_query)

    dados = []
    for r in resultados:
        cnpj = formatar_cnpj(r["cnpj_basico"], r["cnpj_ordem"], r["cnpj_dv"])
        nome = r.get("razao_social", "Desconhecida")
        capital = r.get("capital_social", 0)

        # Conversão segura de capital para float e formatação BRL
        try:
            if isinstance(capital, str):
                capital = capital.replace("R$", "").replace(".", "").replace(",", ".").strip()
            capital = float(capital)
        except (ValueError, TypeError, AttributeError):
            capital = 0.0

        capital_formatado = f"R$ {capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        tipo = "Matriz" if r.get("matriz_filial") == "1" else "Filial"

        situacoes = {
            "01": "NULA",
            "1": "NULA",
            "02": "ATIVA",
            "2": "ATIVA",
            "03": "SUSPENSA",
            "3": "SUSPENSA",
            "04": "INAPTA",
            "4": "INAPTA",
            "08": "BAIXADA",
            "8": "BAIXADA",
        }
        situacao = situacoes.get(str(r.get("situacao_cadastral", "")).zfill(2), "Desconhecida")

        telefone = ""
        ddd = r.get("ddd1")
        tel = r.get("telefone1")
        if ddd and tel:
             telefone = f"({ddd}) {tel}"

        email = r.get("email", "—")

        dados.append({
            "cnpj_completo": cnpj,
            "nome_empresa": nome,
            "capital_social": capital_formatado,
            "tipo_unidade": tipo,
            "situacao_cadastral": situacao,
            "telefone": telefone or "—",
            "email": email or "—"
        })

    return {
        "resultados": dados,
        "ultima_pagina": (total + 99) // 100  # Arredondamento para cima
    }

# Lista de UFs disponíveis
@app.get("/ufs")
def listar_ufs():
    ufs = colecao_cnpjs.distinct("uf")
    return sorted(ufs)

# Lista municípios filtrados por UF
@app.get("/municipios")
def listar_municipios(uf: str):
    codigos = colecao_cnpjs.distinct("codigo_municipio", {"uf": uf.upper()})
    municipios = list(colecao_municipios.find({"codigo_municipio": {"$in": codigos}}, {"_id": 0}))
    municipios.sort(key=lambda m: m["municipio_descricao"])
    return municipios

# Lista de CNAEs
@app.get("/cnaes")
def listar_cnaes():
    cnaes = list(colecao_cnaes.find({}, {"_id": 0}))
    cnaes.sort(key=lambda c: c["cnae_descricao"])
    return cnaes

# Página inicial
@app.get("/")
def raiz():
    return FileResponse("template/index.html")

# Arquivos estáticos (JS/CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")
