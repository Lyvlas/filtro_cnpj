from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient

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
def filtrar(uf: str, municipio: str, cnae: str):
    municipio = municipio.zfill(4)

    pipeline = [
        {"$match": {
            "uf": uf.upper(),
            "codigo_municipio": municipio,
            "cnae_fiscal_principal": cnae
        }},
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
            "razao_social": "$empresa_info.razao_social"
        }}
    ]

    resultados = list(colecao_cnpjs.aggregate(pipeline))
    dados = []

    for r in resultados:
        cnpj = formatar_cnpj(r["cnpj_basico"], r["cnpj_ordem"], r["cnpj_dv"])
        nome = r.get("razao_social", "Desconhecida")

        dados.append({
            "cnpj_completo": cnpj,
            "nome_empresa": nome
        })

    # Nome do município para exibir na tabela
    municipio_info = colecao_municipios.find_one({"codigo_municipio": municipio})
    nome_municipio = municipio_info["municipio_descricao"] if municipio_info else "Desconhecido"

    return {
        "resultados": dados,
        "municipio_descricao": nome_municipio
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
