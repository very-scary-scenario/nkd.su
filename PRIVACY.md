# nkd.su privacy policy

You can look at [the history of changes to this document][history] if you want.

[history]: https://github.com/very-scary-scenario/nkd.su/commits/main/PRIVACY.md "the history of this privacy policy"

## who we are

The **admins**, who control the website and the server it runs on; we are
colons and Peter Shillito.

The **elfs**, who deal with getting new music for the library and correcting
metadata issues.

The **host**, Peter Shillito, who runs the show.

We also have a hosting provider, who technically could get access to a lot of
this information, but we don't expect them to. If you want, you can have a look
at [their privacy policy][linode-privacy], too.

[linode-privacy]: https://www.linode.com/legal-privacy/ "Linode's privacy policy"

## things we gather and how they will be used

### track requests

These include:

- an attribution to your account
- the time that they are made
- what tracks they are for
- any comment you write

These will be used to:

- act as public-facing track requests for the radio show
- provide aggregate information to the host to inform playlist decisions

Your requests, comments, and name may also be read and broadcast as part of the
radio show.

### library addition and metadata correction suggestions

These include:

- the information you type into the form
- any contact information you choose to provide

They will be used to:

- improve the library

The website only shows these to elfs and admins, but they are emailed in plain text and will be shared among the elfs.

### account information

This can include:

- tokens for authenticating you against a third-party authentication provider
  (like Twitter, for instance)
- a [hashed][django-password-storage] password
- a screen name and a display name
- an avatar
- email addresses
- URLs of websites you choose to show on your profile page

[django-password-storage]: https://docs.djangoproject.com/en/3.2/topics/auth/passwords/#how-django-stores-passwords "how Django stores passwords"

These will be used to:

- authenticate you
- represent you to other users

Email addresses will be used to issue password reset requests. We may also use
them to notify you about security issues or other things that may require
action from you. We'll never send promotional material or share addresses with
anyone, for any reason, except with our hosting provider, as outlined above.

You can change your names or avatar at any time. Please contact an admin if you
would like to have this information modified or deleted in a way that the
website doesn't give you controls for. Early in the migration away from
Twitter, less of this will be user-modifiable than we would like, but we'll be
working to sort that quickly.

### sessions

Some nkd.su features require the use of a session cookie associated with
information about what you're currently doing. In particular, we store:

- the tracks that you have selected
- which theme (dark, light, or system) you've chosen
- your login status, if you are logged in

These will only ever be used within your browsing session, and expired sessions
are cleared daily.

### webserver logs

These include:

- IP addresses
- time of access
- URLs accessed

Only admins can see these, and they will only ever be used for threat
mitigation.
