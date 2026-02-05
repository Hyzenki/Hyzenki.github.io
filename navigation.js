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

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
        return;
    }

    const interactiveCards = document.querySelectorAll('.glass-panel, .made-item, .skill-item');
    interactiveCards.forEach((card) => {
        card.addEventListener('mousemove', (event) => {
            const rect = card.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            const rotateX = ((y / rect.height) - 0.5) * -5;
            const rotateY = ((x / rect.width) - 0.5) * 5;
            card.style.transform = `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });

    const trail = document.createElement('div');
    trail.className = 'cursor-trail';
    document.body.appendChild(trail);

    let trailTimeout;
    window.addEventListener('mousemove', (event) => {
        trail.style.left = `${event.clientX}px`;
        trail.style.top = `${event.clientY}px`;
        trail.classList.add('visible');

        clearTimeout(trailTimeout);
        trailTimeout = setTimeout(() => {
            trail.classList.remove('visible');
        }, 120);
    });
});
