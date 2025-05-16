from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from typing import Optional
from re import sub

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["local"]
colecao_cnpjs = db["filtro_cnpj"]
colecao_municipios = db["municipio"]
colecao_cnaes = db["cnaes"]
colecao_grupo_cnae = db["grupo_cnae"]
colecao_empresas = db["empresa"]

# Índices
colecao_cnpjs.create_index([("uf", 1), ("codigo_municipio", 1), ("cnae_fiscal_principal", 1)])
colecao_empresas.create_index("cnpj_basico")

# Utilitário: formatar CNPJ
def formatar_cnpj(basico, ordem, dv):
    cnpj = f"{basico.zfill(8)}{ordem.zfill(4)}{dv.zfill(2)}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

# Filtro principal
@app.get("/filtro")
def filtrar(
    uf: str,
    municipio: str,
    cnae: str,
    situacao: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    municipio = municipio.zfill(4)

    cnae = sub(r"[-/]", "", cnae)
    
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

        try:
            if isinstance(capital, str):
                capital = capital.replace("R$", "").replace(".", "").replace(",", ".").strip()
            capital = float(capital)
        except (ValueError, TypeError, AttributeError):
            capital = 0.0

        capital_formatado = f"R$ {capital:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        tipo = "Matriz" if str(r.get("matriz_filial", "")).strip() == "1" else "Filial"

        situacoes = {
            "01": "NULA", "1": "NULA",
            "02": "ATIVA", "2": "ATIVA",
            "03": "SUSPENSA", "3": "SUSPENSA",
            "04": "INAPTA", "4": "INAPTA",
            "08": "BAIXADA", "8": "BAIXADA",
        }
        situacao_desc = situacoes.get(str(r.get("situacao_cadastral", "")).zfill(2), "Desconhecida")

        telefone = "—"
        if r.get("ddd1") and r.get("telefone1"):
            telefone = f"({r['ddd1']}) {r['telefone1']}"

        dados.append({
            "cnpj_completo": cnpj,
            "nome_empresa": nome,
            "capital_social": capital_formatado,
            "tipo_unidade": tipo,
            "situacao_cadastral": situacao_desc,
            "telefone": telefone,
            "email": r.get("email", "—")
        })

    return {
        "resultados": dados,
        "ultima_pagina": (total + 99) // 100
    }

# Lista UFs
@app.get("/ufs")
def listar_ufs():
    ufs = colecao_cnpjs.distinct("uf")
    return sorted(ufs)

# Lista municípios por UF
@app.get("/municipios")
def listar_municipios(uf: str):
    codigos = colecao_cnpjs.distinct("codigo_municipio", {"uf": uf.upper()})
    municipios = list(colecao_municipios.find(
        {"codigo_municipio": {"$in": codigos}},
        {"_id": 0}
    ))
    municipios.sort(key=lambda m: m["municipio_descricao"])
    return municipios

# Lista de seções (ex: A - Agricultura...)
@app.get("/grupo_cnae/secoes")
def listar_secoes():
    secoes = colecao_grupo_cnae.distinct("secao_codigo")
    resultados = []
    for secao in secoes:
        doc = colecao_grupo_cnae.find_one({"secao_codigo": secao})
        if doc:
            resultados.append({
                "secao_codigo": secao,
                "secao_descricao": doc.get("secao_descricao", "")
            })
    return sorted(resultados, key=lambda x: x["secao_codigo"])

# Lista de divisões por seção (ex: 01 - Agricultura, pecuária...)
@app.get("/grupo_cnae/divisoes")
def listar_divisoes(secao_codigo: str):
    divisoes = colecao_grupo_cnae.find({"secao_codigo": secao_codigo})
    codigos = set()
    resultados = []
    for doc in divisoes:
        divisao = doc.get("divisao_codigo")
        if divisao and divisao not in codigos:
            resultados.append({
                "divisao_codigo": divisao,
                "divisao_descricao": doc.get("divisao_descricao", "")
            })
            codigos.add(divisao)
    return sorted(resultados, key=lambda x: x["divisao_codigo"])

# Lista de grupos por divisão (ex: 01.1 - Cultivo de arroz...)
@app.get("/grupo_cnae/grupos")
def listar_grupos(divisao_codigo: str):
    grupos = colecao_grupo_cnae.find({"divisao_codigo": divisao_codigo})
    codigos = set()
    resultados = []
    for doc in grupos:
        grupo = doc.get("grupo_codigo")
        if grupo and grupo not in codigos:
            resultados.append({
                "grupo_codigo": grupo,
                "grupo_descricao": doc.get("grupo_descricao", "")
            })
            codigos.add(grupo)
    return sorted(resultados, key=lambda x: x["grupo_codigo"])

# Lista de classes por grupo (ex: 01.11 - Cultivo de arroz em casca...)
@app.get("/grupo_cnae/classes")
def listar_classes(grupo_codigo: str):
    classes = colecao_grupo_cnae.find({"grupo_codigo": grupo_codigo})
    codigos = set()
    resultados = []
    for doc in classes:
        classe = doc.get("classe_codigo")
        if classe and classe not in codigos:
            resultados.append({
                "classe_codigo": classe,
                "classe_descricao": doc.get("classe_descricao", "")
            })
            codigos.add(classe)
    return sorted(resultados, key=lambda x: x["classe_codigo"])


# Lista de CNAEs por classe (ex: 0111-3/01 - Cultivo de arroz em casca...)
@app.get("/grupo_cnae/cnaes")
def listar_cnaes(classe_codigo: str):
    cnaes = colecao_grupo_cnae.find({"classe_codigo": classe_codigo})
    resultados = []
    for doc in cnaes:
        subclasse = doc.get("subclasse_codigo", "")
        subclasse_limpo = sub(r"[-/]", "", subclasse)  # transforma "0111-3/01" em "0111301"
        if subclasse:
            resultados.append({
                "cnae_fiscal_principal": subclasse_limpo,
                "cnae_rotulo": f"{subclasse} - {doc.get('subclasse_descricao', '')}"
            })
    return sorted(resultados, key=lambda x: x["cnae_fiscal_principal"])


# Página inicial
@app.get("/")
def raiz():
    return FileResponse("template/index.html")

# Arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
