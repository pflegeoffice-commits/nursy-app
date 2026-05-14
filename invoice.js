const listEl = document.getElementById("invoiceList");
const createBtn = document.getElementById("createInvoiceBtn");

let invoices = JSON.parse(localStorage.getItem("invoices")) || [];

document.addEventListener("DOMContentLoaded", () => {
  renderInvoices();
});

createBtn.addEventListener("click", () => {
  const newInvoice = {
    id: Date.now(),
    title: "Pflegeleistung",
    amount: Math.floor(Math.random() * 200) + 50,
    status: "offen"
  };

  invoices.push(newInvoice);
  save();
  renderInvoices();
});

function save(){
  localStorage.setItem("invoices", JSON.stringify(invoices));
}

function renderInvoices(){
  listEl.innerHTML = "";

  invoices.forEach(inv => {
    const row = document.createElement("div");
    row.className = "invoice-row";

    row.innerHTML = `
      <div>
        <div class="invoice-title">${inv.title}</div>
        <div>${inv.status}</div>
      </div>

      <div class="invoice-amount">${inv.amount} €</div>

      <div class="invoice-actions">
        <button onclick="toggleStatus(${inv.id})">Status</button>
        <button onclick="deleteInvoice(${inv.id})">Löschen</button>
      </div>
    `;

    listEl.appendChild(row);
  });
}

function toggleStatus(id){
  invoices = invoices.map(i =>
    i.id === id
      ? {...i, status: i.status === "offen" ? "bezahlt" : "offen"}
      : i
  );
  save();
  renderInvoices();
}

function deleteInvoice(id){
  invoices = invoices.filter(i => i.id !== id);
  save();
  renderInvoices();
}
