const BASE_URL = window.location.origin;
let paginaAtual = 1;
let ultimaPagina = 1;

window.onload = () => {
    carregarUFs();
    carregarSecoesCNAE();

    document.getElementById("uf").addEventListener("change", carregarMunicipios);
    document.getElementById("secaoSelect").addEventListener("change", carregarDivisoesPorSecao);
    document.getElementById("divisaoSelect").addEventListener("change", carregarGruposPorDivisao);
    document.getElementById("grupoSelect").addEventListener("change", carregarClassesPorGrupo);
    document.getElementById("classeSelect").addEventListener("change", carregarSubclassesPorClasse);

    document.getElementById("consultarBtn").addEventListener("click", () => {
        paginaAtual = 1;
        consultar();
    });
};

// --------------------- UFs e Municípios ---------------------
async function carregarUFs() {
    try {
        const res = await fetch(`${BASE_URL}/ufs`);
        const ufs = await res.json();
        const select = document.getElementById("uf");
        select.innerHTML = `<option value="">Selecione a UF</option>` +
            ufs.map(uf => `<option value="${uf}">${uf}</option>`).join('');
    } catch (error) {
        console.error("Erro ao carregar UFs:", error);
    }
}

async function carregarMunicipios() {
    const uf = document.getElementById("uf").value;
    const select = document.getElementById("municipio");

    resetSelect("municipio");

    if (!uf) {
        select.disabled = true;
        return;
    }

    try {
        const res = await fetch(`${BASE_URL}/municipios?uf=${uf}`);
        const municipios = await res.json();
        select.innerHTML = `<option value="">Selecione o município</option>` +
            municipios.map(m => `<option value="${m.codigo_municipio}">${m.codigo_municipio} - ${m.municipio_descricao}</option>`).join('');
        select.disabled = false;
    } catch (error) {
        console.error("Erro ao carregar municípios:", error);
        select.disabled = true;
    }
}

// --------------------- CNAE em cascata ---------------------
async function carregarSecoesCNAE() {
    try {
        const res = await fetch(`${BASE_URL}/grupo_cnae/secoes`);
        const secoes = await res.json();
        const select = document.getElementById("secaoSelect");
        select.innerHTML = `<option value="">Selecione a Seção</option>` +
            secoes.map(s => `<option value="${s.secao_codigo}">${s.secao_codigo} - ${s.secao_descricao}</option>`).join('');
    } catch (err) {
        console.error("Erro ao carregar seções:", err);
    }
}

async function carregarDivisoesPorSecao() {
    const secao = document.getElementById("secaoSelect").value;
    resetSelect("divisaoSelect");
    resetSelect("grupoSelect");
    resetSelect("classeSelect");
    resetSelect("cnaeSelect");

    if (!secao) return;

    try {
        const res = await fetch(`${BASE_URL}/grupo_cnae/divisoes?secao_codigo=${secao}`);
        const divisoes = await res.json();
        const select = document.getElementById("divisaoSelect");
        select.innerHTML = `<option value="">Selecione a Divisão</option>` +
            divisoes.map(d => `<option value="${d.divisao_codigo}">${d.divisao_codigo} - ${d.divisao_descricao}</option>`).join('');
        select.disabled = false;
    } catch (err) {
        console.error("Erro ao carregar divisões:", err);
    }
}

async function carregarGruposPorDivisao() {
    const divisao = document.getElementById("divisaoSelect").value;
    resetSelect("grupoSelect");
    resetSelect("classeSelect");
    resetSelect("cnaeSelect");

    if (!divisao) return;

    try {
        const res = await fetch(`${BASE_URL}/grupo_cnae/grupos?divisao_codigo=${divisao}`);
        const grupos = await res.json();
        const select = document.getElementById("grupoSelect");
        select.innerHTML = `<option value="">Selecione o Grupo</option>` +
            grupos.map(g => `<option value="${g.grupo_codigo}">${g.grupo_codigo} - ${g.grupo_descricao}</option>`).join('');
        select.disabled = false;
    } catch (err) {
        console.error("Erro ao carregar grupos:", err);
    }
}

async function carregarClassesPorGrupo() {
    const grupo = document.getElementById("grupoSelect").value;
    resetSelect("classeSelect");
    resetSelect("cnaeSelect");

    if (!grupo) return;

    try {
        const res = await fetch(`${BASE_URL}/grupo_cnae/classes?grupo_codigo=${grupo}`);
        const classes = await res.json();
        const select = document.getElementById("classeSelect");
        select.innerHTML = `<option value="">Selecione a Classe</option>` +
            classes.map(c => `<option value="${c.classe_codigo}">${c.classe_codigo} - ${c.classe_descricao}</option>`).join('');
        select.disabled = false;
    } catch (err) {
        console.error("Erro ao carregar classes:", err);
    }
}

async function carregarSubclassesPorClasse() {
    const classe = document.getElementById("classeSelect").value;
    resetSelect("cnaeSelect");

    if (!classe) return;

    try {
        const res = await fetch(`${BASE_URL}/grupo_cnae/cnaes?classe_codigo=${classe}`);
        const cnaes = await res.json();
        const select = document.getElementById("cnaeSelect");
        select.innerHTML = `<option value="">Selecione o CNAE</option>` +
            cnaes.map(c => `<option value="${c.cnae_fiscal_principal}">${c.cnae_rotulo}</option>`).join('');
        select.disabled = false;
    } catch (err) {
        console.error("Erro ao carregar CNAEs:", err);
    }
}

// --------------------- Utilitário ---------------------
function resetSelect(id) {
    const select = document.getElementById(id);
    select.innerHTML = `<option value="">Selecione</option>`;
    select.disabled = true;
}

// --------------------- Consulta e Paginação ---------------------
function mudarPagina(direcao) {
    const novaPagina = paginaAtual + direcao;
    if (novaPagina < 1 || novaPagina > ultimaPagina) return;
    paginaAtual = novaPagina;
    consultar();
}

async function consultar() {
    const uf = document.getElementById("uf").value.trim();
    const municipio = document.getElementById("municipio").value.trim();
    const cnae = document.getElementById("cnaeSelect").value.trim();
    const situacao = document.getElementById("situacao").value;
    const faixaCapital = document.getElementById("faixaCapital").value;
    const loading = document.getElementById("loading");
    const tbody = document.getElementById("resultado-body");
    const paginacaoContainer = document.getElementById("paginacao-container");

    if (!uf || !municipio || !cnae) {
        alert("Preencha todos os campos obrigatórios.");
        return;
    }

    const url = `${BASE_URL}/filtro?uf=${uf}&municipio=${municipio}&cnae=${cnae}&situacao=${situacao}&faixa_capital=${faixaCapital}&page=${paginaAtual}`;
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
                </tr>`;
            paginacaoContainer.classList.add("hidden");
        } else {
            data.resultados.forEach(resultado => {
                const cnpj = resultado.cnpj_completo || '—';
                let nome = resultado.nome_empresa || '—';
                const capital = resultado.capital_social || '—';
                const tipo = resultado.tipo_unidade || '—';
                const telefone = resultado.telefone || '—';
                const email = resultado.email || '—';
                const situacao = resultado.situacao_cadastral || '—';

                // Quebra o nome da empresa depois da 50ª posição
                const pos = nome.indexOf(' ', 50);
                if (pos !== -1) {
                    nome = nome.slice(0, pos) + '<br>' + nome.slice(pos + 1);
                }

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="px-3 py-2 whitespace-nowrap border-b">${cnpj}</td>
                    <td class="px-3 py-2 break-words border-b">${nome}</td>
                    <td class="px-3 py-2 whitespace-nowrap border-b">${capital}</td>
                    <td class="px-3 py-2 whitespace-nowrap border-b">${tipo}</td>
                    <td class="px-3 py-2 border-b">${situacao}</td>
                    <td class="px-3 py-2 whitespace-nowrap border-b">${telefone}</td>
                    <td class="px-3 py-2 break-all text-sm text-gray-600 border-b">${email}</td>`;
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
