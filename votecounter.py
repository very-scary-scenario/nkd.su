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
print '\n'.join(['%s %s' % m for m in most_voted])
