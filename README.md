# Movie Max - Movie Ticket Booking (Flask + MongoDB)

Register / login, browse movies, and book tickets with date, show time and a visual
seat map. A confirmation email is sent to the user's Gmail after booking.
**Admin side:** a separate admin login to add movies and see who booked which tickets.

## Folder structure
```
Movie_Max/
├── app.py                 Flask routes + booking API + admin pages
├── movies.py              the 8 starting movies (edit to change them)
├── requirements.txt       Python packages
├── Procfile               for deployment (gunicorn)
├── render.yaml            optional Render blueprint (see DEPLOY.md)
├── DEPLOY.md              step-by-step: put the site online (Render + Atlas)
├── .env                   YOUR secret settings (edit this!)
├── .env.example           safe template (can be uploaded to GitHub)
├── .gitignore
├── database/mongodb.py    MongoDB connection (users + bookings)
├── utils/email_utils.py   HTML confirmation email (Gmail SMTP)
├── static/
│   ├── image.png          background image (replace with your own)
│   ├── css/style.css      home page styles
│   ├── css/booking.css    booking popup styles
│   ├── js/script.js       search, genre filter, movie details popup
│   └── js/booking.js      date / time / seat map / confirm
└── templates/
    ├── role.html              first page: Continue as User / Login as Admin
    ├── welcome.html           user page: Register as New User / Login
    ├── login.html  register.html  home.html  dashboard.html     (user side)
    └── admin_login.html  admin_base.html  admin_add_movie.html  admin_bookings.html   (admin side)
```

## 1. Run the project (first time)

You need: **Python 3.9+** and **MongoDB** (installed locally, or a free MongoDB Atlas cluster).

**Windows (Command Prompt / VS Code terminal)**
```
cd Movie_Max
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Mac / Linux**
```
cd Movie_Max
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
Open **http://127.0.0.1:5000** in your browser.

Next time, just activate the venv and run `python app.py`.

## 2. Pages and who can open them

| Address | What it is |
|---|---|
| `/` | First page: **Continue as User** or **Login as Admin** |
| `/user` | User page: Register as New User / Login |
| `/register`, `/login` | User registration and login |
| `/home` | Movies + booking (logged-in users only) |
| `/admin/login` | **Admin login only** (there is no admin registration) |
| `/admin/add-movie` | Admin page 1: add a movie |
| `/admin/bookings` | Admin page 2: who booked which tickets |

**Admin ID:** `Satish`  **Password:** `123456`
(change them at the top of `app.py`: `ADMIN_ID` and `ADMIN_PASSWORD`)

### Admin: Add Movie
Fill in title, poster image link, rating (0-10), genre, cast, director, music, description and
**ticket price**. The movie is saved in MongoDB (collection `movies`) and appears on the user
home page straight away. Each movie has its own price; the 8 movies in `movies.py` use the
default `TICKET_PRICE` (Rs. 200).

### Admin: Booked Details
A table of every booking: booking ID, customer name / email / phone, movie, show date and time,
seats, amount, booking time and status - with totals and a search box.

## 3. Edit the .env file (where to insert your details)

Open `.env` in any text editor and change these 4 lines:

| Line | What to put |
|---|---|
| `MONGO_URI=` | Local: `mongodb://localhost:27017` (works if MongoDB is running). Atlas: paste your `mongodb+srv://...` string with your real username and password. |
| `SECRET_KEY=` | Any long random text. |
| `EMAIL_ADDRESS=` | The Gmail that will SEND the emails, e.g. `moviemax2026@gmail.com`. |
| `EMAIL_PASSWORD=` | The 16-letter Gmail **App Password** (next section), no spaces. |

After editing `.env`, **stop the app (Ctrl+C) and run it again**.

## 4. Get a Gmail App Password
Gmail does not allow your normal password for apps. Create an App Password:
1. Open https://myaccount.google.com/security and turn ON **2-Step Verification**.
2. Open https://myaccount.google.com/apppasswords
3. App name: `Movie Max` -> **Create**.
4. Copy the 16-letter password and paste it into `.env` as `EMAIL_PASSWORD=` (remove spaces).

If email is not set up, bookings still work and are saved; the terminal prints
`[EMAIL] ...` explaining why the email was not sent.

## 5. MongoDB notes
- Database: `movie_max`. Collections: `users`, `bookings`, `movies` (created automatically).
- **MongoDB Atlas:** Network Access -> allow your IP (or 0.0.0.0/0 for a college demo),
  and use a database user/password in the connection string.
- View bookings in MongoDB Compass: `movie_max` -> `bookings`.
- A wrongly added movie can be deleted in Compass: `movie_max` -> `movies`.

## 6. Email rule used for register / login
Lowercase letters and digits only, must start with a letter, must end with `@gmail.com`
(e.g. `satish123@gmail.com`). Checked in the browser AND on the server.

## 7. Change booking settings
Top of `app.py`: `TICKET_PRICE`, `SHOW_TIMES`, `SEAT_ROWS`, `SEATS_PER_ROW`, `AISLE_AFTER`,
`MAX_SEATS`, `ADMIN_ID`, `ADMIN_PASSWORD`.

## 8. Deploy (Render + MongoDB Atlas, both free)
Full step-by-step guide: **DEPLOY.md** (Atlas setup, GitHub, Render settings, environment variables, email note).
Quick version:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add `MONGO_URI` and `SECRET_KEY` (and optionally `ADMIN_ID`, `ADMIN_PASSWORD`) as **Environment Variables**
  on Render. Do not upload `.env`.
- Render's free plan blocks Gmail SMTP, so confirmation emails only work locally (bookings still work online).

## Troubleshooting
| Problem | Fix |
|---|---|
| `Could not connect to MongoDB` | Start MongoDB, or fix `MONGO_URI` in `.env`. |
| Email not arriving | Use an App Password, check spam folder, read the `[EMAIL]` message in the terminal. |
| `ModuleNotFoundError` | Activate the venv and run `pip install -r requirements.txt`. |
| Old users cannot log in | Login only accepts valid lowercase Gmail addresses. |
| Background looks plain | Replace `static/image.png` with your own picture. |
