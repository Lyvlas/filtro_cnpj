window.onload = () => {
    carregarUFs();
    carregarCNAEs();
    document.getElementById("uf").addEventListener("change", carregarMunicipios);
};

const BASE_URL = window.location.origin;

async function carregarUFs() {
    try {
        console.log("Carregando UFs...");
        const res = await fetch(`${BASE_URL}/ufs`);
        if (!res.ok) throw new Error("Falha ao carregar UFs.");
        
        const ufs = await res.json();
        console.log("UFs carregadas:", ufs);  // Verificar o que foi retornado
        const select = document.getElementById("uf");
        select.innerHTML = `<option value="">Selecione a UF</option>` + ufs.map(uf => `<option value="${uf}">${uf}</option>`).join('');
    } catch (error) {
        console.error("Erro ao carregar UFs:", error);
    }
}

async function carregarMunicipios() {
    const uf = document.getElementById("uf").value;
    if (!uf) return;

    try {
        console.log("Carregando municípios para UF:", uf);
        const res = await fetch(`${BASE_URL}/municipios?uf=${uf}`);
        if (!res.ok) throw new Error("Falha ao carregar municípios.");
        
        const municipios = await res.json();
        console.log("Municípios carregados:", municipios);  // Verificar o que foi retornado
        const select = document.getElementById("municipio");
        select.innerHTML = `<option value="">Selecione o município</option>` +
            municipios.map(m => 
                `<option value="${m.codigo_municipio}">${m.codigo_municipio} - ${m.municipio_descricao}</option>`
            ).join('');
    } catch (error) {
        console.error("Erro ao carregar municípios:", error);
    }
}

async function carregarCNAEs() {
    try {
        console.log("Carregando CNAEs...");
        const res = await fetch(`${BASE_URL}/cnaes`);
        if (!res.ok) throw new Error("Falha ao carregar CNAEs.");
        
        const cnaes = await res.json();
        console.log("CNAEs carregados:", cnaes);  // Verificar o que foi retornado
        const select = document.getElementById("cnae");
        select.innerHTML = `<option value="">Selecione o CNAE</option>` +
            cnaes.map(c => `<option value="${c.codigo_cnae}">${c.codigo_cnae} - ${c.cnae_descricao}</option>`).join('');
    } catch (error) {
        console.error("Erro ao carregar CNAEs:", error);
    }
}

async function consultar() {
    const uf = document.getElementById("uf").value.trim().toUpperCase();
    const municipio = document.getElementById("municipio").value.trim().padStart(4, '0');
    const cnae = document.getElementById("cnae").value.trim();
    const loading = document.getElementById("loading");
    const tbody = document.getElementById("resultado-body");

    if (!uf || !municipio || !cnae) {
        alert("Preencha todos os campos.");
        return;
    }

    const url = `${BASE_URL}/filtro?uf=${uf}&municipio=${municipio}&cnae=${cnae}`;

    loading.classList.remove("hidden");
    tbody.innerHTML = "";

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        if (data.resultados.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="px-4 py-2 text-center text-gray-500">Nenhum resultado encontrado</td>
                </tr>
            `;
        } else {
            data.resultados.forEach(({ cnpj_completo, nome_empresa }) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="px-4 py-2 text-left border-b">${cnpj_completo}</td>
                    <td class="px-4 py-2 text-left border-b">${nome_empresa}</td>
                    <td class="px-4 py-2 text-left border-b">${data.municipio_descricao}</td>
                    <td class="px-4 py-2 text-left border-b">${data.cnae_descricao}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        alert("Erro ao consultar API: " + err.message);
        console.error(err);
    } finally {
        loading.classList.add("hidden");
    }
}
