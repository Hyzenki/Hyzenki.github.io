document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navLinks = document.querySelector('.nav-links');
    let isMenuOpen = false;

    function toggleMenu() {
        isMenuOpen = !isMenuOpen;
        navLinks.classList.toggle('show');
        mobileMenuButton.setAttribute('aria-expanded', isMenuOpen.toString());
    }

    function closeMenu() {
        isMenuOpen = false;
        navLinks.classList.remove('show');
        mobileMenuButton.setAttribute('aria-expanded', 'false');
    }

    if (mobileMenuButton && navLinks) {
        mobileMenuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMenu();
        });

        // Chiudi menu quando si clicca fuori
        document.addEventListener('click', (e) => {
            if (isMenuOpen && !navLinks.contains(e.target) && !mobileMenuButton.contains(e.target)) {
                closeMenu();
            }
        });

        // Chiudi menu quando si clicca su un link
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', closeMenu);
        });
    }
});

let lastScroll = 0;
const navbar = document.querySelector('.navbar');
const menuIcon = document.createElement('button');
menuIcon.className = 'menu-icon';
menuIcon.innerHTML = '☰';
document.body.appendChild(menuIcon);

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > lastScroll && currentScroll > 60) {
        navbar.classList.add('hidden');
    } else {
        navbar.classList.remove('hidden');
    }
    lastScroll = currentScroll;
});

menuIcon.addEventListener('click', () => {
    const navLinks = document.querySelector('.nav-links');
    navLinks.classList.toggle('show');
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-links') && !e.target.closest('.menu-icon')) {
        document.querySelector('.nav-links').classList.remove('show');
    }
}); 