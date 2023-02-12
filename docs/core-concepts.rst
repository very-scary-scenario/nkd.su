Core concepts of nkd.su
=======================

nkd.su is built with :doc:`Django <django:index>`. Here are some pointers to
key parts of the code.

Types of user
-------------

nkd.su has a few different ways of presenting itself, depending on who is
looking at it. There are:

Anonymous users
   People who aren't signed in. The site is functionally read-only for them.

Normal users
   People signed in to an account, for whom
   :attr:`~django.contrib.auth.models.User.is_authenticated` is :data:`True`.
   They can request music to be played and they can choose how they are
   represented on the website.

Elfs
   Members of the :class:`~django.contrib.auth.models.Group` named :data:`Elfs
   <.ELFS_NAME>`, who will pass the :func:`~.elfs.is_elf` check. These are
   people who deal with sourcing music and metadata for the library. They have
   access to library update requests from users.

Staff
   The host of the show. Represented by
   :attr:`~django.contrib.auth.models.User.is_staff` being :data:`True`.

Models
------

:class:`.Show`
``````````````

Every week, there is a radio broadcast of Neko Desu. Each broadcast corresponds
to a :class:`.Show` in the nkd.su database. By default, these get
:meth:`automatically created <.Show.at>` when necessary, but they can be
created manually or modified on the :doc:`admin site
<django:ref/contrib/admin/index>` for special occasions, like when the show
runs for longer than usual. The show creation logic is kind of horrible and
complicated, because it has to deal with daylight savings time. There are a
fair number of :class:`tests <.ShowTest>` for it, which is reassuring, but I
don't want to touch it again if I don't have to.

:class:`.Track`
```````````````

The library consists of :class:`.Track`\ s, which are populated from an iTunes
library XML export that gets uploaded to :class:`.LibraryUploadView` and
processed by :func:`.update_library()`. During this process, some :func:`checks
<.metadata_consistency_checks>` get run against the existing library, in the
hopes of catching simple errors.

.. _eligibility:

A key property of a :class:`.Track` is its 'eligibility'. This is communicated
in the UI via its background colour; eligible tracks have a light background,
and ineligible tracks have a dark background. This property is influenced by a
lot of things. See :meth:`.Track.ineligible` to learn more.

In addition to this, each user has their own eligibility criteria.
Specifically, :func:`.eligible_for` exists to prevent people from requesting
things twice.

:class:`.Vote`
``````````````

When someone wants a :class:`.Track` to be played on the upcoming (or
currently-airing) :class:`.Show`, they create a :class:`.Vote` for it.

.. note:: User-facing text should be careful about the word 'Vote'. Neko Desu
   is not a democracy, and nkd.su is not a polling website. Current consensus
   is that you should refer to the first :class:`.Vote` filed for a
   :class:`.Track` in a given :class:`.Show` as a 'request'. It is appropriate
   to call any subsequent :class:`.Vote` a vote, though. This distinction is
   communicated in the UI by making the 'request' much more prominent than
   follow-up 'vote'\ s.

   Despite this ambiguity in user-facing names, they should always be called
   :class:`.Vote`\ s in the code and in the database in order to avoid
   confusion with :class:`.Request`, which is a representation of a user's
   request to get a song added or some metadata fixed. To avoid confusion, this
   documentation will use :class:`.Vote` and :class:`.Request` explicitly.

There are three different base types of :class:`.Vote`, enumerated in
:class:`.VoteKind`. In addition, :attr:`~.VoteKind.manual` votes have a number
of subtypes, listed in :data:`.MANUAL_VOTE_KINDS`. We aim to present these as
equivalently as possible in the UI.

The :class:`.VoteKind` of a :class:`.Vote` is not stored explicitly in the
database. Instead, it is calculated based on what attributes are present in
:meth:`.Vote.vote_kind`. To make sure there are no conflicts,
:meth:`.Vote.clean` ensures that only the attributes appropriate for a given
:class:`.VoteKind` are present on any given :class:`.Vote`.

Staff tools
-----------

Staff users can do a lot more things than any other user. They can create
:class:`~.models.Play`\ s to reflect what's being played on air. They can
:class:`.Shortlist` or :class:`.Discard` tracks to help prepare a playlist for
the show. They can perform library updates. They can add public or private
:class:`.Note`\ s. They can force a track to be :ref:`ineligible <eligibility>`
by putting a :class:`.Block` in effect.

For now at least, the full breadth of these features is probably out of scope
for this document. I am currently not sure how to write an introduction to the
inner workings of something for an audience that has never even seen its
intended functionality. I may expand on this in future, though.
