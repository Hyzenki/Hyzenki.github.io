document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navLinks = document.querySelector('.nav-links');

    if (!mobileMenuButton || !navLinks) {
        return;
    }

    let isMenuOpen = false;

    const closeMenu = () => {
        if (!isMenuOpen) {
            return;
        }

        isMenuOpen = false;
        navLinks.classList.remove('show');
        mobileMenuButton.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    };

    const toggleMenu = (event) => {
        event.preventDefault();
        event.stopPropagation();

        isMenuOpen = !isMenuOpen;
        navLinks.classList.toggle('show', isMenuOpen);
        mobileMenuButton.setAttribute('aria-expanded', String(isMenuOpen));
        document.body.style.overflow = isMenuOpen ? 'hidden' : '';
    };

    mobileMenuButton.addEventListener('click', toggleMenu);

    document.addEventListener('click', (event) => {
        if (isMenuOpen && !navLinks.contains(event.target) && !mobileMenuButton.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    });

    navLinks.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', closeMenu);
    });
});
