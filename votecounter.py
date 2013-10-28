from vote.models import Week
from collections import Counter


week = Week()
votes = week._votes()

tracks = []

while votes:
    for vote in votes:
        for track in vote.get_tracks():
            tracks.append((week, track))

    week = week.prev()
    votes = week._votes()

counter = Counter(tracks)

most_voted = counter.most_common(100)
print '\n'.join([(u'%s %s %s' % (m[1], m[0][0].showtime.date().isoformat(),
                                 m[0][1].canonical_string())).encode('utf-8')
                 for m in most_voted])
