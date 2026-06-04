document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('.scroll-section');
    const body = document.body;

    // Theme mapping
    // const themes = {
    //     'section-0': '#000000', // Title Black
    //     'section-1': '#1a0f0f', // Warm dark
    //     'section-2': '#2a1212', // Warmer
    //     'section-3': '#0f121a', // Cool/Neutral
    //     'section-4': '#0f1a18', // Tech/Greenish
    //     'section-5': '#1a1a1a', // Dark Data
    //     'section-6': '#2a1212', // Alert Red-ish
    //     'section-7': '#1a150f', // Insight Brown-ish
    //     'section-8': '#000000'  // Footer Black
    // };

    const themes = {
        'section-0': '#2a1212', // Title Black
        'section-1': '#2a1212', // Warm dark
        'section-2': '#2a1212', // Warmer
        'section-3': '#2a1212', // Cool/Neutral
        'section-4': '#2a1212', // Tech/Greenish
        'section-5': '#2a1212', // Dark Data
        'section-6': '#2a1212', // Alert Red-ish
        'section-7': '#2a1212', // Insight Brown-ish
        'section-8': '#2a1212'  // Footer Black
    };

    const observerOptions = {
        root: document.querySelector('.story-container'),
        threshold: 0.5
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Add active class for animations
                entry.target.classList.add('active');

                // Change background color based on section
                const sectionId = entry.target.id;
                if (themes[sectionId]) {
                    body.style.backgroundColor = themes[sectionId];
                }
            } else {
                // Optional: Remove active class to re-trigger animations when scrolling back
                // entry.target.classList.remove('active'); 
            }
        });
    }, observerOptions);

    sections.forEach(section => {
        observer.observe(section);
    });
});
