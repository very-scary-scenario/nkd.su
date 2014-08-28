## Endpoints

The root of the API is [nkd.su/api/][api_root]. The following endpoints are
available:

### [`/week/<dd>-<mm>-<yyyy>/`][eg_week]

Information from a particular week. The week returned will be the week that was
in progress at midnight on the morning of the day specified.

Includes:

- `votes`: a list of votes placed
- `playlist`: a list of tracks played and the times at which they were played
- `added`: a list of all the tracks added to the library this week
- `start`: the date and time at which this week started
- `finish`: the date and time at which this week ended 
- `showtime`: the date and time at which this week's show began
- `broadcasting`: if this show is on the air at the time of the request
- `message_markdown` and `message_html`: the message shown on the front page
  during the week containing this show

### [`/week/`][eg_latest_week]

A redirect to the week containing the most recent complete show.

### [`/`][api_root]

Information about the week in progress.

### [`/track/<track_id>/`][eg_track]

Information about a particular track, including metadata and a list of every
play on record.

Note that the `plays` list is only included for tracks in calls to
`/track/<track_id>`; tracks returned as part of other endpoints will not have
`plays` listed.

### [`/search/?q=query`][eg_search]

Return a list of `track` objects matching `q`, using the same machinery as the
search box on the website.

## More things

If you're going to create tweets for voters, make sure that '@nkdsu' appears at
the start of the vote tweet. Right now, URLs are constructed in a particular
way and can fall anywhere within a vote tweet, but this is subject to change.
To be safe, keep the URLs before any text and use the `url` value provided in
track objects.

If there is something else you want added or changed, or if you find something
that's broken, [file a bug][new_issue] or just [yell at me][pester] on Twitter.

[new_issue]: https://github.com/colons/nkd.su/issues/new
[api_root]: https://nkd.su/api/
[eg_track]: https://nkd.su/api/track/7C4D7B4B394E0E59/
[eg_latest_week]: https://nkd.su/api/week/
[eg_week]: https://nkd.su/api/week/05-01-2013/
[eg_search]: https://nkd.su/api/search/?q=character%20song
[pester]: https://twitter.com/intent/tweet?text=%40mftb
