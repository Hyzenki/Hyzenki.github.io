document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navLinks = document.querySelector('.nav-links');
    let isMenuOpen = false;

    function toggleMenu(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        isMenuOpen = !isMenuOpen;
        navLinks.classList.toggle('show');
        mobileMenuButton.setAttribute('aria-expanded', isMenuOpen.toString());
        document.body.style.overflow = isMenuOpen ? 'hidden' : '';
    }

    function closeMenu() {
        if (isMenuOpen) {
            isMenuOpen = false;
            navLinks.classList.remove('show');
            mobileMenuButton.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
        }
    }

    if (mobileMenuButton && navLinks) {
        mobileMenuButton.addEventListener('click', toggleMenu);
        
        document.addEventListener('click', (e) => {
            if (isMenuOpen && !navLinks.contains(e.target) && !mobileMenuButton.contains(e.target)) {
                closeMenu();
            }
        });

        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', closeMenu);
        });
    }
}); 