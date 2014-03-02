# emergency recovery procedure for when i get hit by a bus

nkd.su is a reasonably standard Django app. There are some settings that you'll
need to get in order to make it go, though, and some of it requires the use of
stuff I'm supposed to keep secret. If I *do* get hit by a bus, though, it'd be
cool if the site could continue to work.

Here, then, are some instructions that I'm pretty sure should be all you need
to do to get the site up and running on your own server. A passing familiarity
with Django will help greatly. I'm assuming you have a server of some kind that
has Python 2.7 and Apache or nginx or some httpd capable of hosting WSGI apps
installed.

- Talk to Peter. He has some passwords and keys and other things that you'll
  want if you're going to set up a replacement instance.
- Make and activate a virtualenv.
    - I use [virtualenvwrapper][vew]. I
      strongly recommend you do the same.
- Clone the repository.
- `pip install -r requirements.txt` from the repository root.
- Create a `nkdsu/settings_local.py` with `CONSUMER_KEY`, `CONSUMER_SECRET`,
  `READING_ACCESS_TOKEN`, `READING_ACCESS_TOKEN_SECRET`, `POSTING_ACCESS_TOKEN`
  and `POSTING_ACCESS_TOKEN_SECRET`.
    - `READING_` is for @nkdsu, `POSTING_` is for @NekoDesuRadio. Peter has
      keys for all of these already, but you should be able to create a new app
      and get him to reauthenticate them if you want to use your own app keys.
    - If you're setting up an instance for local development and testing, you
      probably want to create a testing Twitter account and use that instead,
      for both `READING_` and `POSTING_`. You may or may not also want to
      override `READING_USERNAME` in your local settings.
- Set up a database and add the [settings][db] for it to your
  `settings_local.py`.
    - I used to use sqlite but now use postgresql. sqlite has problems,
      although I do still use it for my local development instance.
- `python manage.py syncdb --all`
    - This will ask you to set up an account. Make yourself one. We'll make
      Peter's later (assuming you're not Peter).
- `python manage.py migrate`
- `python manage.py loaddata [fixtures]`
    - I have a cron job that dumps the important parts of my instance of nkd.su
      nightly to a json file that Peter has access to. Get that off him and
      replace `[fixtures]` with the path to that file.
- Set up a `MEDIA_ROOT` directory and a `MEDIA_URL` that is pointed at it, then
  run `python manage.py collectstatic`
    - Requires less (the node app, not the pager; available on npm) to be
      installed and for `lessc` to be accessible in your `PATH`.
    - Not necessary for development instances where the `DEBUG` setting is
      true; [Pipeline][pl] will host static media transparently in development.

That *should* be enough that you can run `python manage.py runserver` or point
your apache/nginx/whatever instance at the WSGI app defined in `nkdsu/wsgi.py`
and have the site run. There's still some stuff to do if you want to be able
to accept votes and generally be responsible, though:

- Get the streaming API client up and running.
    - This is the thing that should be importing votes for you. You can fire it
      up with `python manage.py listen_for_votes`. I recommend setting up a
      [supervisor](http://supervisord.org/) instance to look after that, but
      running it in a screen or tmux session will probably do in a pinch.
- Set up some more management commands (stuff you run by invoking `python
  manage.py [command]`) as cron jobs.
    - Just in case the streaming API misses stuff or goes down for a period of
      time, you should run the `refresh_votes` management command every two
      minutes or so.
    - So that we don't start getting broken images for Twitter users who've
      changed their avatar since they last voted, you should run the
      `update_broken_twitter_avatars` management command daily.
    - To keep track album art up to date, you should run the
      `update_background_art` command at least once a week.
    - It would be super considerate to run the `dumpdata vote` command piped to
      a file that is hosted such that Peter can get to it, just in case you too
      are hit by a bus.
- Make Peter an account.
    - You can do this from the admin interface at /admin. Make him a super
      user. Do not make accounts for anyone else; any authenticated user can do
      all the built-in admin stuff like updating the library and hiding tracks.

----

As well as the stuff noted above, Peter has auth details for my nic.ru
account, so if you want to point nkd.su at your server, you should be able to
do that too.

[db]: https://docs.djangoproject.com/en/dev/ref/settings/#databases
[vew]: http://virtualenvwrapper.readthedocs.org/
[pl]: http://django-pipeline.readthedocs.org/
