const BASE_URL = window.location.origin;

window.onload = () => {
    carregarLeads();
};

async function carregarLeads() {
    const tbody = document.getElementById("resultado-body");
    tbody.innerHTML = "";

    try {
        const res = await fetch(`${BASE_URL}/leads`);
        if (!res.ok) throw new Error("Erro ao buscar leads salvos");

        const leads = await res.json();

        if (!leads.length) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-gray-500 py-4">Nenhuma lead salva.</td></tr>`;
            return;
        }

        leads.forEach(lead => {
            // ✅ Nome do lead
            const titulo = document.createElement("tr");
            titulo.innerHTML = `<td colspan="9" class="bg-blue-50 text-blue-700 px-6 py-2 font-semibold">${lead.nome}</td>`;
            tbody.appendChild(titulo);

            lead.dados.forEach(dado => {
                const tr = document.createElement("tr");
                tr.className = "border-b";
                tr.innerHTML = `
                    <td class="px-6 py-3 whitespace-nowrap text-sm">${dado.cnpj}</td>
                    <td class="px-6 py-3 text-sm">${dado.empresa}</td>
                    <td class="px-6 py-3 text-sm">${dado.capital_social}</td>
                    <td class="px-6 py-3 text-sm">${dado.classe_cnae}</td>
                    <td class="px-6 py-3 text-sm">${dado.cnae_descricao}</td>
                    <td class="px-6 py-3 text-sm">${dado.telefone}</td>
                    <td class="px-6 py-3 text-sm">${dado.email}</td>
                `;
                tbody.appendChild(tr);
            });
        });

    } catch (err) {
        console.error("Erro:", err);
        alert("Erro ao carregar leads: " + err.message);
    }
}
