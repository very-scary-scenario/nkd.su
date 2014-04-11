## What is this?

[nkd.su](https://nkd.su) is a request-gathering and voting service for [The
Cat](http://thisisthecat.com)'s [Neko Desu](http://nekodesu.co.uk) radio show.
Songs are sorted according to which was voted for most recently on the front
page.

### How do I vote?

If there are any songs on the front page you would like to vote for, click on
the ‘+1’ next to the current votes and send the generated tweet. If nothing on
the front page strikes your fancy, feel free to use the search box to find
something more your style. Once you've found something, click ‘request this
song’ (or ‘+1’ if it has already been voted for). If you can't find what you're
looking for, fill out the [request an addition](https://nkd.su/request) form.

You can personalise your vote with a message that will appear when people hover
over your user icon. All text that is not either a valid song ID number or the
[@nkdsu](https://twitter.com/nkdsu) mention at the start of the tweet will be
displayed.

If you have javascript enabled, You can select tracks so that you can vote for
several at once by clicking anywhere in a track box that is not a link.

None of your Twitter followers will see your vote in their timelines unless
they're also following [@nkdsu](https://twitter.com/nkdsu).

### All this is well and good but I don't have a Twitter account

You should! It's a neat thing! If you're determined not to join, though, you
could just send Peter an [email](mailto:peter.shillito@thisisthecat.com) or a
text or something.

## How does it work?

Short answer: [Django](https://www.djangoproject.com).

Long answer: [GitHub](https://github.com/colons/nkd.su).
[Suggestions][new_issue] welcome.

## Does it work?

Hopefully! Only Travis knows for sure:

[![Build Status](https://travis-ci.org/colons/nkd.su.svg)](https://travis-ci.org/colons/nkd.su)

## Can I build things with this data?

Totally! There's a JSON API documented [here](https://nkd.su/info/api/). If
there's some data you want that isn't currently surfaced in that API, [let me
know][new_issue].

## Who's to blame?

[Iain Dawson](http://www.musicfortheblind.co.uk/)
([@mftb](https://twitter.com/mftb)), with design contributions from
[Chris Walden](http://www.chriswalden.co.uk)
([@EuricaeriS](https://twitter.com/EuricaeriS)) and
[Peter Shillito](https://twitter.com/theshillito) himself.

[new_issue]: https://github.com/colons/nkd.su/issues/new
