# Docker Setup

## Prereq
You'll want to grab Docker from their website (http://docs.docker.com/installation/) and once that is done you'll need to grab Compose (http://docs.docker.com/compose/install/).

## Getting setup
1. You'll need to create a `settings_local.py` file in `nkdsu/` with API Keys for the following variables:
  - `CONSUMER_KEY` = Twitter API Key
  - `CONSUMER_SECRET` = Twitter API Key
  - `READING_ACCESS_TOKEN` = For @nkdsu
  - `READING_ACCESS_TOKEN_SECRET` = For @nkdsu
  - `POSTING_ACCESS_TOKEN_SECRET` = For @NekoDesuRadio
  - `POSTING_ACCESS_TOKEN_SECRET` = For @NekoDesuRadio
  - `LASTFM_API_KEY` = LastFM
  - `LASTFM_API_SECRET` = LastFM
2. In `docker-compose.yml` change the `POSTGRES_PASSWORD` to be whatever you want. Just remember it for the next step.
2. Also in `nkdsu/settings_local.py` add the following:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'POSTGRESS_PASSWORD',
        'HOST': 'db',
        'PORT': 5432,
    }
}
```
These are the details for our Postgres Database Container we'll be creating in a sec. **Remember to change `POSTGRES_PASSWORD` to whatever you change it to in Step2**
3. Open up your terminal in the root of the project where the `Dockerfile` is located and run `docker-compose run web python manage.py syncdb --all` to create your admin user.
4. Next run `docker-compose run web python manage.py migrate`
5. For the next step you'll need the fixtures file that Colons/Peter has access to. I download it into `nkdsu/db/` but remember where-ever you put it.
6. Run `docker-compose run web python manage.py loaddata [location_of_json_file]` to import the data into our database. This may take a few minutes.
7. You may or may not want to run `docker-compose run web python manage.py collectstatic` depending on whether you have `DEBUG` set to false or not. If `DEBUG` is true then Pipeline will host static media transparently for you.
8. Finally run `docker-compose up` to start the site up.
