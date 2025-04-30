async function consultar() {
    const uf = document.getElementById("uf").value.trim().toUpperCase();
    const municipio = document.getElementById("municipio").value.trim();
    const cnae = document.getElementById("cnae").value.trim();
    const loading = document.getElementById("loading");
    const tbody = document.querySelector("#resultado tbody");

    if (!uf || !municipio || !cnae) {
        alert("Preencha todos os campos.");
        return;
    }

    const url = `http://localhost:8000/filtro?uf=${uf}&municipio=${municipio}&cnae=${cnae}`;

    loading.classList.remove("hidden");
    tbody.innerHTML = "";

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();


        if (data.resultados.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-4 py-2 text-center text-gray-500">Nenhum resultado encontrado</td>
                </tr>
            `;
        } else {
            data.resultados.forEach(({ cnpj_completo }) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="px-4 py-2 text-left border-b" colspan="3">${cnpj_completo}</td>
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
