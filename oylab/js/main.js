document.addEventListener('DOMContentLoaded', () => {

    // --- Анимация появления элементов при прокрутке ---
    const animatedElements = document.querySelectorAll('.scroll-animate');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1
    });
    animatedElements.forEach(element => {
        observer.observe(element);
    });

    // --- АНИМАЦИЯ СЧЕТЧИКА ---
    const counterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = +counter.getAttribute('data-target');
                
                let current = 0;
                const duration = 1500; // Длительность анимации в мс
                const stepTime = 15; 
                const totalSteps = duration / stepTime;
                const increment = target / totalSteps;

                const updateCounter = () => {
                    current += increment;
                    if (current < target) {
                        counter.innerText = Math.ceil(current);
                        setTimeout(updateCounter, stepTime);
                    } else {
                        counter.innerText = target; 
                    }
                };
                
                updateCounter();
                observer.unobserve(counter); 
            }
        });
    }, {
        threshold: 0.8
    });
    
    document.querySelectorAll('.js-counter').forEach(counter => {
        counterObserver.observe(counter);
    });

    // --- Логика для мобильного "бургер"-меню ---
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarMenu = document.querySelector('.navbar-nav');

    navbarToggler.addEventListener('click', () => {
        navbarMenu.classList.toggle('active');
    });
});