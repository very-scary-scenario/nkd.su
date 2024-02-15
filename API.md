## Endpoints

The root of the API is [nkd.su/api/][api_root]. The following endpoints are
available:

### [`/week/<yyyy>-<mm>-<dd>/`][eg_week]

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

If there is something else you want added or changed, or if you find something
that's broken, file a bug on [Codeberg][new_issue_codeberg] or [GitHub][new_issue_github].

[new_issue_codeberg]: https://codeberg.org/very-scary-scenario/nkdsu/issues/new
[new_issue_github]: https://github.com/very-scary-scenario/nkd.su/issues/new
[api_root]: https://nkd.su/api/
[eg_track]: https://nkd.su/api/track/7C4D7B4B394E0E59/
[eg_latest_week]: https://nkd.su/api/week/
[eg_week]: https://nkd.su/api/week/2013-01-05/
[eg_search]: https://nkd.su/api/search/?q=character%20song
