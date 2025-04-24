async function consultar() {
    const uf = document.getElementById("uf").value.trim().toUpperCase();
    const municipio = document.getElementById("municipio").value.trim();
    const cnae = document.getElementById("cnae").value.trim();

    if (!uf || !municipio || !cnae) {
        alert("Preencha todos os campos.");
        return;
    }

    const url = `http://localhost:8000/filtro?uf=${uf}&municipio=${municipio}&cnae=${cnae}`;

    try {
        const res = await fetch(url);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const dados = await res.json();

        const tbody = document.querySelector("#resultado tbody");
        tbody.innerHTML = "";

        if (dados.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="px-4 py-2 text-center t   ext-gray-500">Nenhum resultado encontrado</td></tr>`;
            return;
        }

        dados.forEach(({ cnpj_basico, cnpj_ordem, cnpj_dv }) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="px-4 py-2 text-left border-b">${cnpj_basico}</td>
                <td class="px-4 py-2 text-center border-b">${cnpj_ordem}</td>
                <td class="px-4 py-2 text-center border-b">${cnpj_dv}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        alert("Erro ao consultar API: " + err   .message);
        console.error(err);
    }
}
