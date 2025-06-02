from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from typing import Optional
from re import sub
from fastapi import Request
from pydantic import BaseModel
from datetime import datetime
from fastapi.encoders import jsonable_encoder

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
colecao_leads = db["lead"]

# Índices
colecao_cnpjs.create_index([("uf", 1), ("codigo_municipio", 1), ("cnae_fiscal_principal", 1)])
colecao_empresas.create_index("cnpj_basico")

# Utilitário: formatar CNPJ
def formatar_cnpj(basico, ordem, dv):
    cnpj = f"{basico.zfill(8)}{ordem.zfill(4)}{dv.zfill(2)}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

@app.get("/filtro")
def filtrar(
    uf: str,
    municipio: Optional[str] = "",
    secao: Optional[str] = "",
    divisao: Optional[str] = "",
    grupo: Optional[str] = "",
    classe: Optional[str] = "",
    subclasse: Optional[str] = "",
    cnae: Optional[str] = "",
    situacao: Optional[str] = "",
    faixa_capital: Optional[str] = "",
    tipo_unidade: Optional[str] = "",
    page: int = Query(1, ge=1)
):
    skip = (page - 1) * 100

    # Monta filtro CNAE
    filtro_cnae = {}
    if secao: filtro_cnae["secao_codigo"] = secao
    if divisao: filtro_cnae["divisao_codigo"] = divisao
    if grupo: filtro_cnae["grupo_codigo"] = grupo
    if classe: filtro_cnae["classe_codigo"] = classe
    if subclasse: filtro_cnae["subclasse_codigo"] = subclasse

    cnaes_filtrados = []
    if cnae:
        cnaes_filtrados = [sub(r"[-/]", "", cnae)]
    elif filtro_cnae:
        cnaes_docs = colecao_grupo_cnae.find(filtro_cnae, {"subclasse_codigo": 1})
        cnaes_filtrados = list({
            sub(r"[-/]", "", doc["subclasse_codigo"])
            for doc in cnaes_docs if "subclasse_codigo" in doc
        })

    # Monta filtro principal
    match_query = {}
    if uf: match_query["uf"] = uf.upper()
    if municipio: match_query["codigo_municipio"] = municipio.zfill(4)
    if situacao: match_query["situacao_cadastral"] = situacao
    if tipo_unidade in {"1", "2"}:
        match_query["matriz_filial"] = tipo_unidade  # "1" para Matriz, "2" para Filial
    if cnaes_filtrados:
        match_query["cnae_fiscal_principal"] = {"$in": cnaes_filtrados}

    # Pipeline
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
        # Adicione este lookup para pegar as descrições do CNAE
        {"$lookup": {
            "from": "grupo_cnae",
            "localField": "cnae_fiscal_principal",
            "foreignField": "subclasse_codigo",
            "as": "cnae_info"
        }},
        {"$unwind": {
            "path": "$cnae_info",
            "preserveNullAndEmptyArrays": True
        }},
    ]

    # Filtro faixa capital
    faixas_capital = {
        "<=100K": {"$lte": 100_000},
        "100K-<=1M": {"$gt": 100_000, "$lte": 1_000_000},
        "1M-<=10M": {"$gt": 1_000_000, "$lte": 10_000_000},
        "10M-<=50M": {"$gt": 10_000_000, "$lte": 50_000_000},
        "50M-<=100M": {"$gt": 50_000_000, "$lte": 100_000_000},
        ">100M": {"$gt": 100_000_000},
    }
    if faixa_capital in faixas_capital:
        pipeline.append({
            "$addFields": {
                "capital_float": {
                    "$toDouble": {
                        "$replaceAll": {
                            "input": {
                                "$replaceAll": {
                                    "input": {"$ifNull": ["$empresa_info.capital_social", "0,00"]},
                                    "find": ".",
                                    "replacement": ""
                                }
                            },
                            "find": ",",
                            "replacement": "."
                        }
                    }
                }
            }
        })
        pipeline.append({
            "$match": {
                "capital_float": faixas_capital[faixa_capital]
            }
        })

    pipeline.append({
        "$project": {
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
            "capital_social": {"$ifNull": ["$empresa_info.capital_social", "0,00"]},
            "classe_cnae": {"$ifNull": ["$cnae_info.classe_descricao", "—"]},  # <- descrição da classe
            "cnae_principal_descricao": {"$ifNull": ["$cnae_info.subclasse_descricao", "—"]}
        }
    })

    resultados = list(colecao_cnpjs.aggregate(pipeline))
    total = colecao_cnpjs.count_documents(match_query)

    dados = []
    for r in resultados:
        cnpj = formatar_cnpj(r["cnpj_basico"], r["cnpj_ordem"], r["cnpj_dv"])
        nome = r.get("razao_social", "Desconhecida")
        capital = r.get("capital_social", "0,00")

        try:
            if isinstance(capital, str):
                capital = capital.replace(".", "").replace(",", ".").strip()
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
            "classe_cnae": r.get("classe_cnae", "—"),
            "cnae_principal_descricao": r.get("cnae_principal_descricao", "—"),
            "tipo_unidade": tipo,
            "situacao_cadastral": situacao_desc,
            "telefone": telefone,
            "email": r.get("email", "—")
        })

    return {
        "resultados": dados,
        "total": total,
        "ultima_pagina": (total + 99) // 100,
        "pagina_atual": page
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

class LeadInput(BaseModel):
    nome: str
    dados: list[dict]

@app.post("/salvar-lead")
async def salvar_lead(request: Request, body: LeadInput):
    if not body.dados:
        return {"erro": "Nenhum dado para salvar"}

    doc = {
        "nome": body.nome,
        "criado_em": datetime.utcnow(),
        "dados": body.dados[:100]  # Limita a 100
    }
    colecao_leads.insert_one(doc)
    return {"mensagem": "Lead salvo com sucesso!"}



@app.get("/leads")
def listar_leads():
    leads = colecao_leads.find({}, {"_id": 0, "nome": 1, "dados": 1, "criado_em": 1}).sort("criado_em", -1)
    return jsonable_encoder(list(leads))  # ✅ Garante que datas e listas estejam no formato JSON


# Página inicial
@app.get("/")
def raiz():
    return FileResponse("template/index.html")

# Arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/template", StaticFiles(directory="template"), name="template")
