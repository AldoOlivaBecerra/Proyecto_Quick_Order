/**
 * QUICK ORDER - JavaScript para el Frontend
 * Incremento 1: Catálogo de Productos
 * Incremento 2: Gestión de Comandas
 */

document.addEventListener('DOMContentLoaded', () => {
    console.info('QUICK ORDER - Sistema inicializado.');

    // Accesibilidad: registrar tarjetas de productos en consola si existen
    const productCards = document.querySelectorAll('.product-card');
    if (productCards.length > 0) {
        console.debug(`Se cargaron ${productCards.length} tarjetas de productos activos en la vista.`);
    }

    // Inicializar gestión dinámica de filas de productos en comandas
    inicializarFormularioComandas();
});

/**
 * Controla la adición y eliminación dinámica de filas de productos
 * en las pantallas de Creación y Edición de Comandas.
 */
function inicializarFormularioComandas() {
    const comandaForm = document.getElementById('comanda-form');
    const btnAddRow = document.getElementById('btn-add-row');
    const tbody = document.getElementById('items-tbody');
    const template = document.getElementById('row-template');

    if (!comandaForm || !btnAddRow || !tbody || !template) {
        return;
    }

    // Evento para agregar nueva fila clonando el template
    btnAddRow.addEventListener('click', () => {
        const clone = template.content.cloneNode(true);
        tbody.appendChild(clone);
    });

    // Delegación de eventos para remover filas
    tbody.addEventListener('click', (event) => {
        const btnRemove = event.target.closest('.btn-remove-row');
        if (!btnRemove) return;

        const rows = tbody.querySelectorAll('.item-row');
        if (rows.length <= 1) {
            alert('La comanda debe contener al menos un producto.');
            return;
        }

        const row = btnRemove.closest('.item-row');
        if (row) {
            row.remove();
        }
    });

    // Validación antes del envío
    comandaForm.addEventListener('submit', (event) => {
        const rows = tbody.querySelectorAll('.item-row');
        if (rows.length === 0) {
            alert('Debe agregar al menos un producto a la comanda.');
            event.preventDefault();
            return;
        }

        let seleccionValida = false;
        rows.forEach(row => {
            const select = row.querySelector('.select-producto');
            const inputCant = row.querySelector('.input-cantidad');
            if (select && select.value) {
                seleccionValida = true;
                if (!inputCant || parseInt(inputCant.value, 10) <= 0) {
                    alert('La cantidad de cada producto debe ser mayor a cero.');
                    event.preventDefault();
                }
            }
        });

        if (!seleccionValida) {
            alert('Por favor seleccione al menos un producto válido.');
            event.preventDefault();
        }
    });
}
