# Deploying Movie Max on Render (free) with MongoDB Atlas (free)

The app code is unchanged. Only these things were added so it can run online:
- `render.yaml` - optional, lets Render create the service for you
- `database/__init__.py`, `utils/__init__.py` - empty files that mark the folders as packages
- `app.py` - 2 lines: the admin ID / password can now ALSO be set with the environment variables
  `ADMIN_ID` / `ADMIN_PASSWORD`. If you do not set them, the old values (`Satish` / `123456`) are used.
- `.env.example` - now lists the optional admin variables
- (`Procfile`, `requirements.txt` already had gunicorn - nothing to change)

Your database needs **no seeding**: the 8 movies come from `movies.py`, and users, bookings and
admin-added movies are created automatically in the database `movie_max`.

---------------------------------------------------------------------------------------------

## Step 1 - MongoDB Atlas (free M0 cluster)
1. Cluster is "Cluster0" (M0 / Free) - that is fine.
2. **Database Access** -> make sure you have a database user + password.
3. **Network Access** -> Add IP Address -> **Allow Access from Anywhere** (`0.0.0.0/0`)
   and **untick "temporary"** (otherwise it is deleted after a few hours / days and the site stops working).
   Render's free plan has no fixed IP address, so this is required.
4. **Connect -> Drivers** -> copy the `mongodb+srv://...` string and put your real password in it.
   If the password has symbols like `@ # / :` use a simpler password or URL-encode it.

## Step 2 - Put the project on GitHub
Upload the **contents of the Movie_Max folder** (so `app.py` is at the top level of the repo).
**Do NOT upload `.env`** - it contains your passwords. (`.gitignore` already ignores it when you use git
commands. If you use the GitHub website's "upload files" button, simply do not drag `.env` in.)

```
cd Movie_Max
git init
git add .
git commit -m "Movie Max"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Step 3 - Create the Render web service
Render dashboard -> **New +** -> **Web Service** -> connect your GitHub repo, then:

| Setting | Value |
|---|---|
| Language / Runtime | Python 3 |
| Branch | main |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Instance Type | **Free** |

Open **Environment** (Environment Variables) and add:

| Key | Value |
|---|---|
| `MONGO_URI` | your Atlas `mongodb+srv://...` string (with the real password) |
| `SECRET_KEY` | any long random text |
| `ADMIN_ID` | *(optional)* your admin id |
| `ADMIN_PASSWORD` | *(recommended)* a new admin password - the site will be public, so do not keep `123456` |

Click **Create Web Service**. After the build you get a link like `https://movie-max.onrender.com`.
(Alternative: choose **New + -> Blueprint** and Render reads `render.yaml`; you then only fill in
`MONGO_URI`, `ADMIN_ID`, `ADMIN_PASSWORD`.)

Every `git push` to GitHub redeploys the site automatically.

---------------------------------------------------------------------------------------------

## Confirmation emails on Render's free plan
Render's free web services **block outgoing SMTP ports 25, 465 and 587**, and Movie Max sends its
Gmail emails through port 465. So on the free plan the email cannot be sent. Nothing breaks:
the booking is saved, and the booking screen says "the confirmation email could not be sent".

- **Recommended:** do NOT add `EMAIL_ADDRESS` / `EMAIL_PASSWORD` on Render. The app then skips the
  email instantly (if you add them, each booking waits about 15 seconds for the blocked connection to time out).
- Emails still work on your own computer with `python app.py` and your `.env`.
- To get real emails online you can (a) upgrade the Render instance to a paid type, or
  (b) switch the email code to an email service that works over HTTPS (for example Brevo's free plan).
  Option (b) needs a small code change in `utils/email_utils.py`.

## After it is live - quick test
1. Open the link (the first visit after a quiet period takes about a minute - the free service sleeps
   after 15 minutes without visitors).
2. Register a user -> open a movie -> Book Tickets -> pick date, time and seats -> Confirm.
3. `/admin/login` -> log in -> **Booked Details** shows the booking.
4. In Atlas -> Browse Collections -> database `movie_max` -> `users`, `bookings`, `movies`.

## If something goes wrong
| Problem | Fix |
|---|---|
| Site loads but register / login / booking fails | `MONGO_URI` is wrong or missing on Render, or Atlas Network Access has no `0.0.0.0/0`. Check Render -> Logs for `[MONGODB] Could not connect`. |
| It worked, then stopped after some days | The temporary `0.0.0.0/0` entry in Atlas expired - add it again as a permanent entry. Or the free cluster was paused - click Resume in Atlas. |
| Build fails | Open the build log. If it names the Python version, add an environment variable `PYTHON_VERSION` = `3.12.3`. |
| "Application failed to respond" / 502 | Start Command must be exactly `gunicorn app:app` and `app.py` must be in the top folder of the repo. |
| Background picture missing | Put your own `image.png` in the `static` folder (it was not part of the files received). |
| Movie posters missing later | The poster links in `movies.py` are Google thumbnail links, which can stop working. Replace them with permanent image links. |
| Logged out after redeploy | Normal if `SECRET_KEY` changed - keep the same value. |

## Security reminders
- Your real Atlas password and Gmail App Password were in the `.env` you shared. Once the site is live,
  change both (Atlas -> Database Access -> Edit user; Google -> App passwords -> create a new one),
  then update `.env` and Render's environment variables.
- Never put `.env` on GitHub.
