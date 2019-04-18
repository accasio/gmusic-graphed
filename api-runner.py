import io
import sys
from threading import Thread
import time

from gmusicapi import Mobileclient
from PIL import Image
import requests
import matplotlib.pyplot as plt

# for testing
# import itertools
# import pickle

verbose = False
waiting = False


def spinning_cursor(prefix):
    while True:
        for cursor in '|/-\\':
            yield '\r%s %s' % (prefix, cursor)


def threaded_cursor(prefix):
    global waiting
    spinner = spinning_cursor(prefix)
    while waiting:
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.3)

    sys.stdout.write("\r%s: done\n" % prefix)


def progress(iteration, total, prefix='', suffix='', decimals=2, length=50, fill='#'):
    # modified from: https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = (fill * filled_length) + '-' * (length - filled_length)

    sys.stdout.write('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix))
    sys.stdout.flush()

    if iteration == total:
        print()


def make_plot(years):
    global waiting
    # with open('years.pickle', 'rb') as handle:
    #     years = pickle.load(handle)

    # years = dict(itertools.islice(years.items(), 2))
    total = sum([len(years[year]) for year in years])
    x_min = int(min(years))
    x_max = int(max(years))
    y_max = 0
    prog = 0

    progress(0, total, prefix='Downloading Artwork:', suffix='Complete')
    for year, albums in sorted(years.items()):
        for y, album in enumerate(albums):
            prog = prog + 1
            if y > y_max:
                y_max = y
            try:
                img = requests.get(album['artwork']).content
                img = Image.open(io.BytesIO(img))
                w_percent = (128/float(img.size[0]))
                height = int((float(img.size[1])*float(w_percent)))
                img = img.resize((128, height), Image.ANTIALIAS)

            except Exception:
                # use a default album artwork in case there is an error 
                img = Image.open('default_album.jpg')

            left = int(year)  # year on x-axis
            right = left + 1
            plt.imshow(img, extent=[left - 0.5, right - 0.5, y, (y + 1)])

            progress(prog, total, prefix='Downloading Artwork:', suffix='Complete')

    waiting = True
    thread = Thread(target=threaded_cursor, args=('Generating Graph',))
    thread.start()
    plt.style.use('fivethirtyeight')
    plt.xlabel('Year')
    plt.ylabel('# Albums')
    plt.xlim(x_min - 1, x_max + 1)
    plt.ylim(0, y_max * 1.1)
    plt.tight_layout()
    plt.savefig('album-graph.jpg', format='jpg', dpi=1200, bbox_inches='tight', pad_inches=0.1)
    waiting = False
    thread.join()
    print('\nNew Graph Available: ./%s' % 'album-graph.jpg')


def main():
    global waiting
    waiting = False
    mc = Mobileclient()
    mc.perform_oauth(storage_filepath='./oauth.cred')
    mc.oauth_login(device_id=mc.FROM_MAC_ADDRESS, oauth_credentials='./oauth.cred')
    waiting = True
    thread = Thread(target=threaded_cursor, args=('Gathering Metadata',))
    thread.start()
    library = mc.get_all_songs()
    years = {}

    for song in library:
        if 'year' in song:
            try:
                if not str(song['year']) in years:
                    years[str(song['year'])] = []

                if any(song['album'] in keys['album'] for keys in years[str(song['year'])]):
                    continue
                else:
                    if 'albumArtRef' in song:
                        d = {'album': song['album'], 'artwork': song['albumArtRef'][0]['url']}
                        years[str(song['year'])].append(d)
                    else:
                        if verbose:
                            print("No album art for {}".format(song))
            except KeyError:
                if verbose:
                    print("Key error {}".format(song))
        else:
            if verbose:
                print("No year for {}".format(song))

    # clean up songs with unknown year
    if '0' in years:
        del years['0']
    waiting = False
    thread.join()
    make_plot(years)


if __name__ == '__main__':
    main()
