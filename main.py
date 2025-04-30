from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
import os

app = FastAPI()

# Libera acesso frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["local"]
colecao_cnpjs = db["filtro_cnpj"]
colecao_municipios = db["municipio"]
colecao_cnaes = db["cnaes"]

def formatar_cnpj(basico, ordem, dv):
    cnpj = f"{basico}{ordem}{dv}"
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]} - {cnpj[12:14]}"

@app.get("/filtro")
def filtrar(
    uf: str = Query(...),
    municipio: str = Query(...),
    cnae: str = Query(...),
):
    municipio = str(municipio).zfill(4)
    print(f"UF: {uf}, Código Município: {municipio}, CNAE: {cnae}")

    query = {
        "uf": uf.upper(),
        "codigo_municipio": municipio,
        "cnae_fiscal_principal": cnae
    }

    cursor = colecao_cnpjs.find(
        query,
        {"_id": 0, "cnpj_basico": 1, "cnpj_ordem": 1, "cnpj_dv": 1}
    ).limit(100)

    resultados_cnpjs = []
    for doc in cursor:
        cnpj_formatado = formatar_cnpj(doc['cnpj_basico'], doc['cnpj_ordem'], doc['cnpj_dv'])
        resultados_cnpjs.append({
            "cnpj_completo": cnpj_formatado
        })

    municipio_doc = colecao_municipios.find_one({"codigo_municipio": municipio}, {"_id": 0, "municipio_descricao": 1})
    descricao_municipio = municipio_doc["municipio_descricao"] if municipio_doc else "Município não encontrado"

    cnae_doc = colecao_cnaes.find_one({"codigo_cnae": cnae}, {"_id": 0, "cnae_descricao": 1})
    descricao_cnae = cnae_doc["cnae_descricao"] if cnae_doc else "CNAE não encontrado"

    return {
        "municipio_descricao": descricao_municipio,
        "cnae_descricao": descricao_cnae,
        "resultados": resultados_cnpjs
    }

@app.get("/")
def home():
    caminho = os.path.join("template", "index.html")
    if not os.path.exists(caminho):
        return {"erro": "index.html não encontrado!"}
    return FileResponse(caminho)

app.mount("/static", StaticFiles(directory="static"), name="static")
