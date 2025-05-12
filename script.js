window.onload = () => {
    carregarUFs();
    carregarCNAEs();
    document.getElementById("uf").addEventListener("change", carregarMunicipios);
};

const BASE_URL = window.location.origin;
let paginaAtual = 1;
let ultimaPagina = 1;

//** Carrega as UFs disponíveis na API e as adiciona ao select */
async function carregarUFs() {
    try {
        const res = await fetch(`${BASE_URL}/ufs`);
        if (!res.ok) throw new Error("Falha ao carregar UFs.");

        const ufs = await res.json();
        const select = document.getElementById("uf");
        select.innerHTML = `<option value="">Selecione a UF</option>` +
            ufs.map(uf => `<option value="${uf}">${uf}</option>`).join('');
    } catch (error) {
        console.error("Erro ao carregar UFs:", error);
    }
}
//** Carrega os municípios disponíveis na API e os adiciona ao select */
async function carregarMunicipios() {
    const uf = document.getElementById("uf").value;
    if (!uf) return;

    try {
        const res = await fetch(`${BASE_URL}/municipios?uf=${uf}`);
        if (!res.ok) throw new Error("Falha ao carregar municípios.");

        const municipios = await res.json();
        const select = document.getElementById("municipio");
        select.innerHTML = `<option value="">Selecione o município</option>` +
            municipios.map(m =>
                `<option value="${m.codigo_municipio}">${m.codigo_municipio} - ${m.municipio_descricao}</option>`
            ).join('');
    } catch (error) {
        console.error("Erro ao carregar municípios:", error);
    }
}
//** Carrega os CNAEs disponíveis na API e os adiciona ao select */
async function carregarCNAEs() {
    try {
        const res = await fetch(`${BASE_URL}/cnaes`);
        if (!res.ok) throw new Error("Falha ao carregar CNAEs.");

        const cnaes = await res.json();
        const select = document.getElementById("cnae");
        select.innerHTML = `<option value="">Selecione o CNAE</option>` +
            cnaes.map(c => `<option value="${c.codigo_cnae}">${c.codigo_cnae} - ${c.cnae_descricao}</option>`).join('');
    } catch (error) {
        console.error("Erro ao carregar CNAEs:", error);
    }
}

function mudarPagina(direcao) {
    const novaPagina = paginaAtual + direcao;
    if (novaPagina < 1 || novaPagina > ultimaPagina) return;
    paginaAtual = novaPagina;
    consultar();
}

async function consultar() {
    const uf = document.getElementById("uf").value.trim().toUpperCase();
    const municipio = document.getElementById("municipio").value.trim().padStart(4, '0');
    const cnae = document.getElementById("cnae").value.trim();
    const situacao = document.getElementById("situacao").value;
    const loading = document.getElementById("loading");
    const tbody = document.getElementById("resultado-body");
    const paginacaoContainer = document.getElementById("paginacao-container");

    if (!uf || !municipio || !cnae) {
        alert("Preencha todos os campos.");
        return;
    }

    const url = `${BASE_URL}/filtro?uf=${uf}&municipio=${municipio}&cnae=${cnae}&situacao=${situacao}&page=${paginaAtual}`;

    loading.classList.remove("hidden");
    tbody.innerHTML = "";

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        ultimaPagina = data.ultima_pagina || 1;
        document.getElementById("paginacao").textContent = `Página ${paginaAtual} de ${ultimaPagina}`;

        if (!data.resultados || data.resultados.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-4 py-2 text-center text-gray-500">Nenhum resultado encontrado</td>
                </tr>
            `;
            paginacaoContainer.classList.add("hidden"); 
        } else {
        
            data.resultados.forEach(resultado => {
                const cnpj = resultado.cnpj_completo || '—';
                let nome = resultado.nome_empresa || '—';
                const capital = resultado.capital_social || '—';
                const tipo = resultado.tipo_unidade || '—'; 
                const telefone = resultado.telefone || '—';
                const email = resultado.email || '—';
                
            
                const pos = nome.indexOf(' ', 50);
                if (pos !== -1) {
                    nome = nome.slice(0, pos) + '<br>' + nome.slice(pos + 1);
                }
            
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="px-4 py-2 text-left border-b whitespace-nowrap font-mono tracking-tight">${cnpj}</td>
                    <td class="px-4 py-2 text-left border-b break-words">${nome}</td>
                    <td class="px-4 py-2 text-left border-b whitespace-nowrap">${capital}</td>
                    <td class="px-4 py-2 text-left border-b whitespace-nowrap">${tipo}</td>
                    <td class="px-4 py-2 border-b">${resultado.situacao_cadastral}</td>
                    <td class="px-4 py-2 border-b whitespace-nowrap">${telefone}</td>
                    <td class="px-4 py-2 border-b ">${email}</td>

                `;
                tbody.appendChild(tr);
            });
            
        
            paginacaoContainer.classList.remove("hidden"); 
        }
        
        document.getElementById("anterior").disabled = paginaAtual === 1;
        document.getElementById("proximo").disabled = paginaAtual === ultimaPagina;

    } catch (err) {
        alert("Erro ao consultar API: " + err.message);
        console.error(err);
    } finally {
        loading.classList.add("hidden");
    }
}
