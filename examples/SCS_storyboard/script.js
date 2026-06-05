document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('.scroll-section');
    const body = document.body;

    const themes = {
        "section-0": "#ffffff",
        "section-1": "#ecf7f7",
        "section-2": "#ecf7f7",
        "section-3": "#eaf3f4",
        "section-4": "#e8f3f4",
        "section-5": "#eef3f4",
        "section-6": "#e1eff3",
        "section-7": "#e8f4f6",
        "section-8": "#ffffff"
    };

    const observerOptions = {
        root: document.querySelector('.story-container'),
        threshold: 0.5
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                const sectionId = entry.target.id;
                if (themes[sectionId]) {
                    body.style.backgroundColor = themes[sectionId];
                }
            }
        });
    }, observerOptions);

    sections.forEach(section => observer.observe(section));
});
