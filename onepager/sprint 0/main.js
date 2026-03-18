function toggleMenu() {
    const navLinks = document.getElementById('navLinks');
    if (window.innerWidth > 700) return;

    const isOpening = !navLinks.classList.contains('active');
    navLinks.classList.toggle('active');

    if (isOpening) {
        navLinks.style.display = 'flex';
        navLinks.style.flexDirection = 'column';
        navLinks.style.overflow = 'hidden';

        navLinks.animate([
            { height: '0px', opacity: 0, transform: 'translateY(-10px)' },
            { height: navLinks.scrollHeight + 'px', opacity: 1, transform: 'translateY(0)' }
        ], {
            duration: 400,
            easing: 'ease-out',
            fill: 'forwards'
        });
    } else {
        const closingAnim = navLinks.animate([
            { height: navLinks.scrollHeight + 'px', opacity: 1, transform: 'translateY(0)' },
            { height: '0px', opacity: 0, transform: 'translateY(-10px)' }
        ], {
            duration: 300,
            easing: 'ease-in',
            fill: 'forwards'
        });

        closingAnim.onfinish = () => {
            if (!navLinks.classList.contains('active')) {
                navLinks.style.display = 'none';
            }
        };
    }
}

window.addEventListener('resize', () => {
    const navLinks = document.getElementById('navLinks');
    if (window.innerWidth > 700) {
        navLinks.style.display = '';
        navLinks.style.flexDirection = '';
        navLinks.style.height = '';
        navLinks.style.opacity = '';
        navLinks.style.transform = '';
        navLinks.classList.remove('active');

        navLinks.getAnimations().forEach(anim => anim.cancel());
    }
});

let currentSlide = 0;
const track = document.getElementById('track');
const slides = track.children;

function moveSlide(direction) {
    currentSlide += direction;

    if (currentSlide < 0) {
        currentSlide = slides.length - 1;
    } else if (currentSlide >= slides.length) {
        currentSlide = 0;
    }

    const moveAmount = -currentSlide * 100;
    track.style.transform = `translateX(${moveAmount}vw)`;
}