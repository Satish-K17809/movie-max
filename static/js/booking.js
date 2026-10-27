// booking.js - the Book Tickets popup: date, show time, seat map, confirm.
// "movies" and "bookingConfig" are defined in home.html (they come from Flask).

const bkOverlay = document.getElementById('bkOverlay');
const bkDates = document.getElementById('bkDates');
const bkTimes = document.getElementById('bkTimes');
const bkSeatMap = document.getElementById('bkSeatMap');
const bkSeatArea = document.getElementById('bkSeatArea');
const bkSeatHint = document.getElementById('bkSeatHint');
const bkConfirmBtn = document.getElementById('bkConfirmBtn');
const bkError = document.getElementById('bkError');

// What the user has chosen so far
let bkMovie = null;          // the movie object from movies.py
let bkDate = '';             // e.g. "2026-10-09"
let bkTime = '';             // e.g. "6:30 PM"
let bkSelected = [];         // e.g. ["A3", "A4"]
let bkBooked = [];           // seats already taken for this movie + date + time

// ---------- Open / close ----------
function openBooking(movie) {
    bkMovie = movie;
    bkDate = '';
    bkTime = '';
    bkSelected = [];
    bkBooked = [];

    // Movie information (left side)
    document.getElementById('bkTitle').textContent = movie.title;
    document.getElementById('bkRating').textContent = '⭐ ' + movie.rating + '/10';
    document.getElementById('bkGenre').textContent = movie.genre.split(',').map(function (g) { return g.trim(); }).join(' • ');
    document.getElementById('bkDirector').textContent = movie.director;
    document.getElementById('bkCast').textContent = movie.cast.slice(0, 4).join(', ');
    document.getElementById('bkFallback').textContent = movie.title;
    const poster = document.getElementById('bkPoster');
    poster.style.display = 'block';
    poster.onerror = function () { poster.style.display = 'none'; };
    poster.src = movie.poster;

    buildDateButtons();
    buildTimeButtons();
    updateSeatArea();

    document.getElementById('bkSelectView').style.display = 'block';
    document.getElementById('bkDoneView').style.display = 'none';
    bkOverlay.classList.add('open');
}

function closeBooking() {
    bkOverlay.classList.remove('open');
}

// ---------- Date + time buttons ----------
function buildDateButtons() {
    bkDates.innerHTML = '';
    bookingConfig.dates.forEach(function (d) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'bk-opt';
        btn.innerHTML = '<small>' + d.weekday + '</small>' + d.label;   // values come from our own server
        btn.addEventListener('click', function () {
            bkDate = d.value;
            markActive(bkDates, btn);
            onChoiceChanged();
        });
        bkDates.appendChild(btn);
    });
}

function buildTimeButtons() {
    bkTimes.innerHTML = '';
    bookingConfig.times.forEach(function (t) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'bk-opt';
        btn.textContent = t;
        btn.addEventListener('click', function () {
            bkTime = t;
            markActive(bkTimes, btn);
            onChoiceChanged();
        });
        bkTimes.appendChild(btn);
    });
}

function markActive(group, activeBtn) {
    group.querySelectorAll('.bk-opt').forEach(function (b) { b.classList.remove('active'); });
    activeBtn.classList.add('active');
}

// Date or time changed -> a different show -> different seats
function onChoiceChanged() {
    bkSelected = [];
    bkBooked = [];
    bkError.textContent = '';
    if (bkDate && bkTime) {
        loadBookedSeats();
    } else {
        updateSeatArea();
    }
}

// Ask Flask (which asks MongoDB) which seats are already booked for this show
function loadBookedSeats() {
    const url = '/api/booked-seats?movie=' + encodeURIComponent(bkMovie.title) +
                '&date=' + encodeURIComponent(bkDate) +
                '&time=' + encodeURIComponent(bkTime);

    fetch(url)
        .then(function (res) { return res.json(); })
        .then(function (data) {
            bkBooked = data.seats || [];
            updateSeatArea();
        })
        .catch(function () {
            bkError.textContent = 'Could not load seats. Please try again.';
        });
}

// ---------- Seat map ----------
function updateSeatArea() {
    if (bkDate && bkTime) {
        bkSeatArea.style.display = 'block';
        const dateLabel = bookingConfig.dates.find(function (d) { return d.value === bkDate; }).label;
        bkSeatHint.textContent = 'Showing seats for ' + dateLabel + ', ' + bkTime + '.';
        drawSeats();
    } else {
        bkSeatArea.style.display = 'none';
        bkSeatHint.textContent = 'Choose a date and a show time to see the seats.';
    }
    updateSummary();
}

function drawSeats() {
    bkSeatMap.innerHTML = '';

    bookingConfig.rows.forEach(function (row) {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'bk-row';

        const label = document.createElement('span');
        label.className = 'bk-rowlabel';
        label.textContent = row;
        rowDiv.appendChild(label);

        for (let n = 1; n <= bookingConfig.perRow; n++) {
            const id = row + n;                       // A1, A2 ...
            const seat = document.createElement('button');
            seat.type = 'button';
            seat.className = 'seat';
            seat.textContent = n;
            seat.title = id;

            if (bkBooked.includes(id)) {
                seat.classList.add('booked');         // taken: cannot be clicked
                seat.disabled = true;
            } else if (bkSelected.includes(id)) {
                seat.classList.add('selected');
            }

            seat.addEventListener('click', function () { toggleSeat(id); });
            rowDiv.appendChild(seat);

            // walking gap (aisle) in the middle of the row
            if (n === bookingConfig.aisleAfter) {
                const gap = document.createElement('span');
                gap.className = 'bk-aisle';
                rowDiv.appendChild(gap);
            }
        }
        bkSeatMap.appendChild(rowDiv);
    });
}

function toggleSeat(id) {
    bkError.textContent = '';
    const pos = bkSelected.indexOf(id);

    if (pos !== -1) {
        bkSelected.splice(pos, 1);                    // click again = deselect
    } else if (bkSelected.length >= bookingConfig.maxSeats) {
        bkError.textContent = 'You can select at most ' + bookingConfig.maxSeats + ' seats.';
        return;
    } else {
        bkSelected.push(id);
    }
    drawSeats();
    updateSummary();
}

// Ticket price of the movie being booked (each movie can have its own price)
function moviePrice() {
    return (bkMovie && bkMovie.price) ? bkMovie.price : bookingConfig.price;
}

// Seats text + automatic price (seats x ticket price)
function updateSummary() {
    const count = bkSelected.length;
    const sorted = bkSelected.slice().sort(function (a, b) {
        return a.charAt(0).localeCompare(b.charAt(0)) || parseInt(a.slice(1)) - parseInt(b.slice(1));
    });

    document.getElementById('bkSummaryText').textContent =
        count === 0 ? 'No seats selected' : 'Seats: ' + sorted.join(', ');
    document.getElementById('bkTotal').textContent =
        count === 0 ? '' : count + ' × ₹' + moviePrice() + ' = ₹' + (count * moviePrice());
    bkConfirmBtn.disabled = (count === 0 || !bkDate || !bkTime);
}

// ---------- Confirm ----------
bkConfirmBtn.addEventListener('click', function () {
    bkConfirmBtn.disabled = true;
    bkConfirmBtn.textContent = 'BOOKING...';
    bkError.textContent = '';

    fetch('/api/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie: bkMovie.title, date: bkDate, time: bkTime, seats: bkSelected })
    })
        .then(function (res) {
            return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (result) {
            bkConfirmBtn.textContent = 'CONFIRM BOOKING';
            if (result.ok) {
                showConfirmation(result.data);
            } else {
                bkError.textContent = result.data.error || 'Booking failed.';
                if (result.data.reload_seats) {       // someone else took a seat first
                    bkSelected = [];
                    loadBookedSeats();
                }
                updateSummary();
            }
        })
        .catch(function () {
            bkConfirmBtn.textContent = 'CONFIRM BOOKING';
            bkError.textContent = 'Network problem. Please try again.';
            updateSummary();
        });
});

// ---------- Booking success screen ----------
function showConfirmation(b) {
    const view = document.getElementById('bkDoneView');
    view.innerHTML = '';

    function add(tag, className, text) {
        const el = document.createElement(tag);
        el.className = className;
        el.textContent = text;
        view.appendChild(el);
        return el;
    }
    function detail(label, value) {
        const row = document.createElement('div');
        row.className = 'bk-detail';
        const a = document.createElement('span');
        const c = document.createElement('span');
        a.textContent = label;
        c.textContent = value;
        row.appendChild(a);
        row.appendChild(c);
        view.appendChild(row);
    }

    add('h3', 'bk-done-title', 'BOOKING CONFIRMED ✓');

    const idBox = document.createElement('div');
    idBox.className = 'bk-ticket-id';
    idBox.innerHTML = '<small>Booking ID</small><strong></strong>';
    idBox.querySelector('strong').textContent = b.booking_id;
    view.appendChild(idBox);

    detail('Movie', b.movie);
    detail('Date', b.date);
    detail('Time', b.time);
    detail('Seats', b.seats.join(', '));
    detail('Tickets', b.seat_count);
    detail('Price', '₹' + b.price + ' × ' + b.seat_count);
    detail('Total', '₹' + b.total);
    detail('Customer', b.name);
    detail('Email', b.email);
    detail('Status', b.status);

    add('p', 'bk-mail-note', b.email_sent
        ? 'A confirmation email has been sent to ' + b.email + '.'
        : 'Your booking is saved, but the confirmation email could not be sent right now.');

    const done = add('button', 'book-btn', 'DONE');
    done.type = 'button';
    done.addEventListener('click', closeBooking);

    document.getElementById('bkSelectView').style.display = 'none';
    view.style.display = 'block';
}

// ---------- Wiring ----------
// The "BOOK TICKETS" button inside the movie details popup
document.getElementById('bookBtn').addEventListener('click', function () {
    const title = document.getElementById('modalTitle').textContent;
    const movie = movies.find(function (m) { return m.title === title; });
    if (movie) { openBooking(movie); }
});

document.getElementById('bkClose').addEventListener('click', closeBooking);
bkOverlay.addEventListener('click', function (e) {
    if (e.target === bkOverlay) { closeBooking(); }
});
