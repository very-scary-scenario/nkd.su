# emergency recovery procedure for when i get hit by a bus

nkd.su is a reasonably standard Django app. There are some settings that you'll
need to get in order to make it go, though, and some of it requires the use of
stuff I'm supposed to keep secret. If I *do* get hit by a bus, though, it'd be
cool if the site could continue to work.

Here, then, are some instructions that I'm pretty sure should be all you need
to do to get the site up and running on your own server. A passing familiarity
with Django will help greatly. I'm assuming you have a server of some kind that
has Python 3.11 and Apache or nginx or some httpd capable of hosting WSGI apps
installed.

- Talk to Peter. They have some passwords and keys and other things that you'll
  want if you're going to set up a replacement instance.
- Make sure you have Python 3.11 or newer and some kind of recent version of
  npm.
- Make and activate a [virtualenv][venv].
    - I use [virtualenvwrapper][vew], but it's up to you how to set this up.
- Clone the repository.
- Run `pip install -r requirements.txt` from the repository root to install
  Python requirements.
- Run `npm install` from the repository root to install the node tools used for
  static file preprocessing and linting.
- Create a `nkdsu/settings_local.py`
    - [Make some last.fm API keys][lastfmapikeys] and add them as
      `LASTFM_API_KEY` and `LASTFM_API_SECRET`.
- Set up a database and add the [settings][db] for it to your
  `settings_local.py`.
    - The site runs on postgresql. It will run on other backends, but searches
      won't be as good. You'll need to `CREATE EXTENSION unaccent;` on the
      database to make searches not 500 on postgresql.
- `python manage.py migrate`
    - This will ask you to set up an account. Make yourself one. We'll make
      Peter's later (assuming you're not Peter).
- `python manage.py loaddata [fixtures]`
    - I have a cron job that dumps the important parts of my instance of nkd.su
      nightly to a json file that Peter has access to. Get that off them and
      replace `[fixtures]` with the path to that file.
- Set up a `MEDIA_ROOT` directory and a `MEDIA_URL` that is pointed at it, then
  run `python manage.py collectstatic`
    - Not necessary for development instances where the `DEBUG` setting is
      true; [Pipeline][pl] will host static media transparently in development.

That *should* be enough that you can run `python manage.py runserver` or point
your apache/nginx/whatever instance at the WSGI app defined in `nkdsu/wsgi.py`
and have the site run. There's still some stuff to do if you want to be able
to accept votes and generally be responsible, though:

- Set up some more management commands (stuff you run by invoking `python
  manage.py [command]`) as cron jobs.
    - You should run the `refresh_votes` management command every two minutes
      or so.
    - You should run the `clearsessions` management command daily.
    - To keep track album art up to date, you should run the
      `update_background_art` command at least once a week.
    - It would be super considerate to run the `dumpdata vote` command piped to
      a file that is hosted such that Peter can get to it, just in case you too
      are hit by a bus.
- Make Peter an account with staff and admin permissions.
    - You can do this from the admin interface at /admin. Make them a super
      user.
- Make non-staff accounts for the elfs who gather tracks, so that they can get
  to the request list

----

As well as the stuff noted above, Peter has auth details for my nic.ru
account, so if you want to point nkd.su at your server, you should be able to
do that too.

[lastfmapikeys]: http://www.last.fm/api/account/create
[db]: https://docs.djangoproject.com/en/dev/ref/settings/#databases
[venv]: https://docs.python.org/3.11/tutorial/venv.html#tut-venv
[vew]: https://virtualenvwrapper.readthedocs.io/
[pl]: https://django-pipeline.readthedocs.io/
