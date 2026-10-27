// script.js - search, genre filter and the movie details popup.
// "movies" (the list from movies.py) is defined in home.html.
// The Book Tickets button is handled in booking.js.

const searchInput = document.getElementById('searchInput');
const cards = document.querySelectorAll('.movie-card');
const chips = document.querySelectorAll('.chip');
const noResults = document.getElementById('noResults');

let activeGenre = '';   // the genre button currently selected ('' = none)

// ---------- Search + genre filter ----------
function filterMovies() {
    const text = searchInput.value.trim().toLowerCase();
    let visible = 0;

    cards.forEach(function (card) {
        const matchesText = card.dataset.title.includes(text) || card.dataset.genre.includes(text);
        const matchesGenre = activeGenre === '' || card.dataset.genre.includes(activeGenre.toLowerCase());

        if (matchesText && matchesGenre) {
            card.classList.remove('hidden');
            visible++;
        } else {
            card.classList.add('hidden');
        }
    });

    noResults.style.display = (visible === 0) ? 'block' : 'none';
}

searchInput.addEventListener('input', filterMovies);

chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
        if (activeGenre === chip.dataset.genre) {
            activeGenre = '';                       // click again = clear
            chip.classList.remove('active');
        } else {
            activeGenre = chip.dataset.genre;
            chips.forEach(function (c) { c.classList.remove('active'); });
            chip.classList.add('active');
        }
        filterMovies();
    });
});

// ---------- Movie details popup ----------
const overlay = document.getElementById('modalOverlay');
const modalPoster = document.getElementById('modalPoster');

function openModal(index) {
    const m = movies[index];

    document.getElementById('modalTitle').textContent = m.title;
    document.getElementById('modalRating').textContent = '⭐ ' + m.rating + '/10';
    document.getElementById('modalGenre').textContent = m.genre.split(',').map(function (g) { return g.trim(); }).join(' • ');
    document.getElementById('modalDirector').textContent = m.director;
    document.getElementById('modalMusic').textContent = m.music;
    document.getElementById('modalDesc').textContent = m.description;
    document.getElementById('modalFallback').textContent = m.title;

    // Cast list
    const castList = document.getElementById('modalCast');
    castList.innerHTML = '';
    m.cast.forEach(function (actor) {
        const li = document.createElement('li');
        li.textContent = actor;
        castList.appendChild(li);
    });

    // Poster (hidden automatically if the image file is missing)
    modalPoster.style.display = 'block';
    modalPoster.onerror = function () { modalPoster.style.display = 'none'; };
    modalPoster.src = m.poster;
    modalPoster.alt = m.title + ' poster';

    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';    // stop page scrolling behind the popup
}

function closeModal() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
}

cards.forEach(function (card) {
    card.addEventListener('click', function () { openModal(card.dataset.index); });
});

document.getElementById('modalClose').addEventListener('click', closeModal);

// Click on the dark area (outside the white box) closes the popup
overlay.addEventListener('click', function (e) {
    if (e.target === overlay) { closeModal(); }
});

// Esc closes the booking popup first (if open), otherwise the details popup
document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') { return; }
    const booking = document.getElementById('bkOverlay');
    if (booking.classList.contains('open')) {
        booking.classList.remove('open');
    } else {
        closeModal();
    }
});
