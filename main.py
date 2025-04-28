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

# Endpoint de filtro atualizado
@app.get("/filtro")
def filtrar(
    uf: str = Query(...),
    municipio: str = Query(...),
    cnae: str = Query(...),
):
    # Ajusta o código do município para ser sempre uma string de 4 dígitos
    municipio = str(municipio).zfill(4)  # Adiciona zeros à esquerda se necessário
    
    print(f"UF: {uf}, Código Município: {municipio}, CNAE: {cnae}")  # Log para verificar os parâmetros de entrada
    
    # Construção da query de CNPJs
    query = {
        "uf": uf.upper(),
        "codigo_municipio": municipio,
        "cnae_fiscal_principal": cnae
    }

    # Consulta aos CNPJs
    resultados_cnpjs = list(colecao_cnpjs.find(
        query,
        {"_id": 0, "cnpj_basico": 1, "cnpj_ordem": 1, "cnpj_dv": 1}
    ).limit(100))

    # Log para verificar os resultados dos CNPJs
    print(f"Resultados CNPJs: {resultados_cnpjs}")

    # Busca a descrição do município
    print(f"Consultando município com código: {municipio}")  # Log de município
    municipio_doc = colecao_municipios.find_one({"codigo_municipio": municipio}, {"_id": 0, "municipio_descricao": 1})
    
    # Verifica se a descrição do município foi encontrada
    if municipio_doc:
        print(f"Descrição do Município Encontrada: {municipio_doc['municipio_descricao']}")
        descricao_municipio = municipio_doc["municipio_descricao"]
    else:
        print(f"Descrição do Município NÃO encontrada para o código: {municipio}")
        descricao_municipio = "Município não encontrado"
    
    # Busca a descrição do CNAE
    cnae_doc = colecao_cnaes.find_one({"codigo_cnae": cnae}, {"_id": 0, "cnae_descricao": 1})
    
    # Verifica se a descrição do CNAE foi encontrada
    if cnae_doc:
        print(f"Descrição do CNAE Encontrada: {cnae_doc['cnae_descricao']}")
        descricao_cnae = cnae_doc["cnae_descricao"]
    else:
        print("Descrição do CNAE NÃO encontrada.")
        descricao_cnae = "CNAE não encontrado"

    return {
        "municipio_descricao": descricao_municipio,
        "cnae_descricao": descricao_cnae,
        "resultados": resultados_cnpjs
    }

# Servir página HTML
@app.get("/")
def home():
    caminho = os.path.join("template", "index.html")
    if not os.path.exists(caminho):
        return {"erro": "index.html não encontrado!"}
    return FileResponse(caminho)

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
