from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient

app = FastAPI()

# Libera o CORS
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

# Indexação para performance
colecao_cnpjs.create_index([("uf", 1), ("codigo_municipio", 1), ("cnae_fiscal_principal", 1)])
colecao_empresas.create_index("cnpj_basico")

def formatar_cnpj(basico, ordem, dv):
    cnpj = f"{basico}{ordem}{dv}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"

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
        dados.append({"cnpj_completo": cnpj, "nome_empresa": nome})

    mun = colecao_municipios.find_one({"codigo_municipio": municipio}, {"_id": 0, "municipio_descricao": 1})
    cnae_doc = colecao_cnaes.find_one({"codigo_cnae": cnae}, {"_id": 0, "cnae_descricao": 1})

    return {
        "municipio_descricao": mun["municipio_descricao"] if mun else "Não encontrado",
        "cnae_descricao": cnae_doc["cnae_descricao"] if cnae_doc else "Não encontrado",
        "resultados": dados
    }

@app.get("/")
def raiz():
    return FileResponse("template/index.html")

# Arquivos estáticos (JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")
