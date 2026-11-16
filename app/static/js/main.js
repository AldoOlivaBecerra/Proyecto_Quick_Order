/**
 * QUICK ORDER - JavaScript para el Frontend
 * Incremento 1: Catálogo de Productos
 */

document.addEventListener('DOMContentLoaded', () => {
    console.info('QUICK ORDER - Módulo de Productos inicializado.');

    // Accesibilidad: registrar tarjetas de productos en consola si existen
    const productCards = document.querySelectorAll('.product-card');
    if (productCards.length > 0) {
        console.debug(`Se cargaron ${productCards.length} tarjetas de productos activos en la vista.`);
    }
});
