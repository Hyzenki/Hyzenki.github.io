document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navLinks = document.querySelector('.nav-links');

    // Toggle menu
    mobileMenuButton.addEventListener('click', (e) => {
        e.stopPropagation();
        navLinks.classList.toggle('show');
    });

    // Chiudi menu quando si clicca su un link
    const links = document.querySelectorAll('.nav-links a');
    links.forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('show');
        });
    });

    // Chiudi menu quando si clicca fuori
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.navbar')) {
            navLinks.classList.remove('show');
        }
    });

    // Gestisci la navigazione
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            // Chiudi il menu prima della navigazione
            navLinks.classList.remove('show');
        });
    });
}); 