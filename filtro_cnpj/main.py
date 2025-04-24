from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
import os

app = FastAPI()

# Libera o acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com o Mongo
client = MongoClient("mongodb://localhost:27017/")
db = client["local"]
colecao = db["filtro_cnpj"]

# Endpoint de filtro
@app.get("/filtro")
def filtrar(
    uf: str = Query(...),
    municipio: str = Query(...),
    cnae: str = Query(...)
):
    query = {
        "uf": uf.upper(),
        "codigo_municipio": municipio,
        "cnae_fiscal_principal": cnae
    }
    resultados = colecao.find(
        query,
        {"_id": 0, "cnpj_basico": 1, "cnpj_ordem": 1, "cnpj_dv": 1}
    ).limit(100)

    return list(resultados)

# Servir a página HTML principal
@app.get("/")
def home():
    caminho = os.path.join("template", "index.html")
    if not os.path.exists(caminho):
        return {"erro": "index.html não encontrado!"}
    return FileResponse(caminho)

# Servir arquivos estáticos (como JS ou CSS, se usar)
app.mount("/static", StaticFiles(directory="static"), name="static")
