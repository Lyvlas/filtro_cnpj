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

    console.log(`Consultando API com os parâmetros: UF=${uf}, Município=${municipio}, CNAE=${cnae}`); // Log de parâmetros antes da consulta

    loading.classList.remove("hidden");
    tbody.innerHTML = "";

    try {
        const res = await fetch(url);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();

        console.log("Resposta da API:", data); // Log da resposta da API

        // Atualiza o cabeçalho com as descrições (se existirem)
        const municipioTitulo = document.getElementById("municipioDescricao");
        const cnaeTitulo = document.getElementById("cnaeDescricao");

        if (municipioTitulo) {
            municipioTitulo.textContent = `Município: ${data.municipio_descricao || "Descrição não encontrada"}`;
        }
        if (cnaeTitulo) {
            cnaeTitulo.textContent = `CNAE: ${data.cnae_descricao || "Descrição não encontrada"}`;
        }

        if (data.resultados.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-4 py-2 text-center text-gray-500">
                        Nenhum resultado encontrado
                    </td>
                </tr>
            `;
        } else {
            data.resultados.forEach(({ cnpj_basico, cnpj_ordem, cnpj_dv }) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="px-4 py-2 text-left border-b">${cnpj_basico}</td>
                    <td class="px-4 py-2 text-center border-b">${cnpj_ordem}</td>
                    <td class="px-4 py-2 text-center border-b">${cnpj_dv}</td>
                    <td class="px-4 py-2 text-left border-b">${data.municipio_descricao || "Descrição não encontrada"}</td>
                    <td class="px-4 py-2 text-left border-b">${data.cnae_descricao || "Descrição não encontrada"}</td>
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
