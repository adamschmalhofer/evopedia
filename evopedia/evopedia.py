#!/usr/bin/python
# coding=utf8

# evopedia, offline Wikipedia reader
# Copyright (C) 2009 Christian Reitwiessner <christian@reitwiessner.de>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, see
# <http://www.gnu.org/licenses/>.


from __future__ import with_statement
from __future__ import division

import cgi
import shutil
from os import path, listdir, walk, readlink
import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urllib import unquote_plus, unquote, quote, pathname2url
from xml.sax import saxutils
import math
from math import floor, ceil
import re
import operator
import time
import threading
from random import randint, choice
import urllib2

# do not put slashes at the end here!
config = {'storage': 'datafile',
          'static_path': '/usr/lib/evopedia/static'}

try:
    import dbus
except ImportError:
    dbus = None

try:
    math.atanh(0)
except AttributeError:
    math.atanh = lambda x: .5 * (math.log(1 + x) - math.log(1 - x))

endpattern = re.compile('(_[0-9a-f]{4})?(\.html(\.redir)?)?$')


class EvopediaHandler(BaseHTTPRequestHandler):
    TILESIZE = 256
    map_width = 400
    map_height = 380

    def output_wiki_page(self, url):
        global storage
        global config

        text = storage.get_article_by_name(url)
        if text is None:
            self.output_error_page()
        else:
            self.write_header(use_cache=1)
            with open(path.join(config['static_path'], 'header.html')) as head:
                shutil.copyfileobj(head, self.wfile)
            (lat, lon) = self.get_coords_in_article(text)
            if lat is not None and lon is not None:
                self.wfile.write(('<a class="evopedianav" ' +
                        'href="/map/?lat=%f&lon=%f&zoom=13">' +
                        '<img src="/static/maparticle.png"></a>') %
                                 (lat, lon))
            self.wfile.write(('<a class="evopedianav" href="%s">' +
                    '<img src="/static/wikipedia.png"></a>') %
                    storage.get_orig_url(url))
            self.wfile.write('</div>')
            self.wfile.write(text)
            with open(path.join(config['static_path'], 'footer.html')) as foot:
                shutil.copyfileobj(foot, self.wfile)

    def output_error_page(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(path.join(config['static_path'], 'header.html')) as head:
            shutil.copyfileobj(head, self.wfile)
        self.wfile.write("</div>ERROR - Page not found")
        with open(path.join(config['static_path'], 'footer.html')) as foot:
            shutil.copyfileobj(foot, self.wfile)

    def output_error_msg_page(self, msg):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(path.join(config['static_path'], 'header.html')) as head:
            shutil.copyfileobj(head, self.wfile)
        self.wfile.write((u"</div>ERROR: %s" % msg).encode('utf-8'))
        with open(path.join(config['static_path'], 'footer.html')) as foot:
            shutil.copyfileobj(foot, self.wfile)

    def output_search_result(self, query, limit):
        self.write_header('text/xml')
        self.wfile.write("<?xml version='1.0' encoding='UTF-8' ?>\n")
        try:
            self.wfile.write(self.get_search_result_text(query, limit)
                             .encode('utf-8'))
        except Exception, e:
            self.wfile.write(('<error>%s</error>' %
                              saxutils.escape(repr(e))).encode('utf-8'))

    # XXX check if used
    def get_article_name_from_filename(self, filename):
        return endpattern.sub('', filename).replace('_', ' ')

    def get_search_result_text(self, query, limit):
        global storage

        text = ''
        titles = storage.get_titles_with_prefix(query)
        for (i, title) in enumerate(titles):
            if i >= limit:
                return '<list complete="0">' + text + '</list>'
            else:
                title = saxutils.escape(title[0])
                text += '<article name="%s" url="/wiki/%s" />' % (title, title)
        return '<list complete="1">' + text + '</list>'

    def get_coords_in_article(self, text):
        lat = lng = None

        m = re.search('params=(\d*)_(\d*)_([0-9.]*)_(N|S)'
                      '_(\d*)_(\d*)_([0-9.]*)_(E|W)', text)
        if m:
            (lat, lng) = self.parse_coordinates_dms(m)
        else:
            m = re.search('params=(\d*\.\d*)_(N|S)_(\d*\.\d*)_(E|W)', text)
            if m:
                (lat, lng) = self.parse_coordinates_dec(m)
        return (lat, lng)

    def splice_coords(self, coords):
        (head, rest) = ('%012.7f' % coords).split('.')
        head1 = head[:-1]
        head2 = head[-1]
        return [head[:-1], head[-1]] + list(rest[:1])

    def parse_coordinates_dec(self, match):
        try:
            lat = float(match.group(1))
            if match.group(2) == 'S':
                lat *= -1
            lon = float(match.group(3))
            if match.group(4) == 'W':
                lon *= -1
            return (lat, lon)
        except ValueError:
            return (None, None)

    def parse_coordinates_dms(self, match):
        try:
            groups = [match.group(i) for i in (1, 2, 3, 5, 6, 7)]
            for i in range(len(groups)):
                try:
                    groups[i] = float(groups[i])
                except ValueError:
                    groups[i] = 0
            lat = groups[0] + groups[1] / 60 + groups[2] / 3600
            if match.group(4) == 'S':
                lat *= -1
            lon = groups[3] + groups[4] / 60 + groups[5] / 3600
            if match.group(8) == 'W':
                lon *= -1
            return (lat, lon)
        except ValueError:
            return (None, None)

    def output_map(self, coords, zoom):
        TILESIZE = self.TILESIZE

        self.write_header()

        with open(path.join(config['static_path'], 'mapheader.html')) as head:
            shutil.copyfileobj(head, self.wfile)

        global tangogps_tilerepos

        (tx, ty) = self.coords2pixel(zoom, coords)

        # XXX "repr" below could behave a bit different than expected
        #     but we'll see.
        text = (u'<script type="text/javascript">' +
                u'var map = new MapHandler(%d, %d, %d, %s);</script>' %
                (zoom, tx, ty, repr([x.title for x in tangogps_tilerepos])))

        self.wfile.write(text.encode('utf-8'))

        with open(path.join(config['static_path'], 'footer.html')) as foot:
            shutil.copyfileobj(foot, self.wfile)

    def output_geo_articles(self, zoom, minx, miny, maxx, maxy):
        global storage

        self.write_header('text/xml')
        self.wfile.write("<?xml version='1.0' encoding='UTF-8' ?>\n")

        mincoords = self.pixel2coords(zoom, (minx, maxy))
        maxcoords = self.pixel2coords(zoom, (maxx, miny))

        try:
            self.wfile.write(u'<articles>'.encode('utf-8'))

            articlecount = 0
            for (name, lat, lon, url) in storage.titles_in_coords(mincoords,
                                                                 maxcoords):
                (x, y) = self.coords2pixel(zoom, (lat, lon))
                self.wfile.write(((u'<article name="%s" x="%d" y="%d" ' +
                                   u'href="%s"/>') %
                                   (saxutils.escape(name.encode('utf-8')), x, y,
                                    quote(url))).encode('utf-8'))
                articlecount += 1
                if articlecount > 100:
                    self.wfile.write((u'<error>Zoom in for more articles.' +
                                      u'</error>').encode('utf-8'))
                    break

            self.wfile.write((u'</articles>').encode('utf-8'))
        except IOError:
            print("geo request cancelled by browser")

    def coords2pixel(self, zoom, coords):
        TILESIZE = self.TILESIZE
        (lat, lon) = coords
        lon = lon / 360 + 0.5
        lat = math.atanh(math.sin(lat / 180 * math.pi))
        lat = - lat / (2 * math.pi) + 0.5
        scale = 2 ** zoom * TILESIZE
        return (int(lon * scale), int(lat * scale))

    def pixel2coords(self, zoom, pixel):
        TILESIZE = self.TILESIZE
        (x, y) = pixel
        scale = 2 ** zoom * TILESIZE
        lon = (x / scale - 0.5) * 360
        lat = - (y / scale - 0.5) * 2 * math.pi
        lat = math.asin(math.tanh(lat)) * 180 / math.pi
        return (lat, lon)

    def coordpath_in_limits(self, path, mincoords, maxcoords):
        lon = int(path[0]) * 10 + int(path[2])
        lat = int(path[1]) * 10 + int(path[3])

    def write_header(self, content_type='text/html', use_cache=0):
        self.send_response(200)
        if use_cache:
            # XXX test if caching is really relevant (browser does not use it)
            # XXX Use real time (could be time-consuming)
            #self.send_header('Last-Modified', 'Thu, 01 Jan 1970 00:00:00 GMT')
            pass
        self.send_header('Content-type', content_type + '; charset=UTF-8')
        self.end_headers()

    def decode(self, s):
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError:
            try:
                s = s.decode('latin-1')
            except UnicodeDecodeError:
                pass
        return s

    def do_GET(self):
        global config

        dict = None
        i = self.path.rfind('?')
        if i >= 0:
            self.path, query = self.path[:i], self.path[i + 1:]
            if query:
                dict = cgi.parse_qs(query)

        parts = [self.decode(unquote(i)) for i in self.path.split('/') if i]

        if len(parts) == 0:
            # XXX Compare file dates (could be time-consuming), use
            # headers.getdate('If...')
            if self.headers.get('If-Modified-Since') is not None:
                self.send_response(304)
                self.end_headers()
                return
            self.write_header(use_cache=1)
            with open(path.join(config['static_path'],
                                'search.html')) as search:
                shutil.copyfileobj(search, self.wfile)
            return
        elif parts[0] == 'static':
            # XXX Compare file dates (could be time-consuming)
            if self.headers.get('If-Modified-Since') is not None:
                self.send_response(304)
                self.end_headers()
                return
            if len(parts) == 2 and parts[1] in set(['search.js', 'main.css',
                    'search.html', 'mapclient.js', 'map.js', 'zoomin.png',
                    'zoomout.png', 'search.png', 'wikipedia.png', 'close.png',
                    'random.png', 'map.png', 'maparticle.png', 'home.png',
                    'crosshairs.png']):
                if parts[1].endswith('.png'):
                    self.write_header('image/png', use_cache=1)
                elif parts[1].endswith('.css'):
                    self.write_header('text/css', use_cache=1)
                elif parts[1].endswith('.js'):
                    self.write_header('application/javascript', use_cache=1)
                else:
                    self.write_header(use_cache=1)
                with open(path.join(config['static_path'], parts[1])) as fobj:
                    shutil.copyfileobj(fobj, self.wfile)
                return
        elif parts[0] == 'search':
            try:
                query = self.decode(dict['q'][0])
            except (UnicodeDecodeError, TypeError, KeyError):
                query = ''
            self.output_search_result(query, 50)
            return
        elif parts[0] == 'map':
            try:
                coords = (float(dict['lat'][0]), float(dict['lon'][0]))
            except (ValueError, KeyError, TypeError):
                coords = (50, 10)

            try:
                zoom = int(dict['zoom'][0])
            except (ValueError, KeyError, TypeError):
                zoom = 3

            self.output_map(coords, zoom)
            return
        elif parts[0] == 'maptile':
            # XXX Compare file dates (could be time-consuming)
            if self.headers.get('If-Modified-Since') is not None:
                print("cache hit")
                self.send_response(304)
                self.end_headers()
                return
            try:
                (repoindex, z, x, y) = parts[1:5]
                y = y.split('.')[0]
                global tangogps_tilerepos
                tangogps_tilerepos[int(repoindex)]\
                        .output_map_tile(self, int(x), int(y), int(z))
            except Exception, e:
                self.output_error_msg_page('Invalid URL')
                import traceback
                traceback.print_exc()
            return
        elif parts[0] == 'geo':
            try:
                minx = int(dict['minx'][0])
                miny = int(dict['miny'][0])
                maxx = int(dict['maxx'][0])
                maxy = int(dict['maxy'][0])
                zoom = int(dict['zoom'][0])
            except (ValueError, KeyError, TypeError):
                self.output_error_msg_page('Invalid URL')
                return
            self.output_geo_articles(zoom, minx, miny, maxx, maxy)
            return
        elif parts[0] == 'gpspos':
            try:
                zoom = int(dict['zoom'][0])
            except (ValueError, KeyError, TypeError):
                self.output_error_msg_page('Invalid URL')
                return

            global gps_handler

            pos = gps_handler.get_gps_pos()
            self.write_header('text/xml')
            self.wfile.write("<?xml version='1.0' encoding='UTF-8' ?>\n")
            if pos is False:
                self.wfile.write('<error>No GPS Fix</error>')
                return

            (coordx, coordy) = self.coords2pixel(zoom, pos)

            self.wfile.write('<position x="%d" y="%d" zoom="%d"/>' %
                             (coordx, coordy, zoom))

            return
        elif parts[0] == 'random':
            title = storage.get_random_article()
            if title is not None:
                self.send_response(302)
                self.send_header('Location', pathname2url('/wiki/' +
                                                title.encode('utf-8')))
                self.end_headers()
            else:
                self.output_error_msg_page("Error finding random page...")
            return
        elif parts[0] in ('wiki', 'articles'):
            if 'If-Modified-Since' in self.headers:
                self.send_response(304)
                self.end_headers()
                return
            if parts[0] == 'articles':
                # compatibility for squashfs-style links in datafile storage
                url = endpattern.sub('', parts[-1]).replace('_', ' ')
            else:
                url = '/'.join(parts[1:])
            self.output_wiki_page(url)
            return

        self.output_error_page()


class GPSHandler(object):

    def __init__(self):
        self.dbus = None
        self.ousaged = None
        self.gypsy = None
        self.gps_release_timer = None

        self.gps_activated = False
        self.last_gps_usage = 0

        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        while True:
            try:
                if self.gps_activated and \
                   self.last_gps_usage < time.time() - 5 * 60:
                    self.release_gps()
                time.sleep(60)
            except Exception, e:
                print e

    def init_dbus(self):
        if dbus is None:
            return False
        try:
            if self.dbus is None:
                self.dbus = dbus.SystemBus()
            gypsy_object = self.dbus.get_object("org.freedesktop.Gypsy",
                                                "/org/freedesktop/Gypsy")
            self.gypsy = dbus.Interface(gypsy_object,
                                        "org.freedesktop.Gypsy.Position")
            ousaged_object = self.dbus.get_object("org.freesmartphone.ousaged",
                                                  "/org/freesmartphone/Usage")
            self.ousaged = dbus.Interface(ousaged_object,
                                          "org.freesmartphone.Usage")
        except dbus.exceptions.DBusException, e:
            print e
            if self.gypsy is None:
                return False
            return True

    def request_gps(self):
        self.last_gps_usage = time.time()
        if self.gps_activated:
            return
        try:
            self.ousaged.RequestResource("GPS")
            self.gps_activated = True
        except Exception, e:
            print e

    def update_gps_release_timer(self):
# XXX don't use timer but interval that checks the last usage timestamp
        if self.gps_release_timer is not None:
            self.gps_release_timer.cancel()
        self.gps_release_timer = threading.Timer(5 * 60, self.release_gps)
        self.gps_release_timer.start()

    def get_gps_pos(self):
        if self.gypsy is None:
            if not self.init_dbus():
                return False

        self.request_gps()

        (valid, tstamp, lat, lng, alt) = self.gypsy.GetPosition()

        if lat != 0 and lng != 0:
            return (lat, lng)
        else:
            return False

    def release_gps(self):
        self.gps_activated = False
        if self.ousaged is None:
            return
        print("Releasing GPS...")
        self.ousaged.ReleaseResource("GPS")


class TileRepo(object):

    def __init__(self, title, tileurl, tilepath, zoom_last=False):
        self.title = title
        self.tileurl = saxutils.unescape(tileurl)
        self.tilepath = tilepath
        self.zoom_last = zoom_last

        if tilepath is not None and not path.isdir(tilepath):
            self.tilepath = None

    def __str__(self):
        return u'Tile Repository "%s" (%s, %s)' % (self.title, self.tilepath,
                                                   self.tileurl)

    def output_map_tile(self, request_handler, x, y, zoom):
        if self.tilepath is not None:
            if self.get_local_tile(request_handler, x, y, zoom):
                return

        self.redirect_to_remote_tile(request_handler, x, y, zoom)
        #self.send_remote_tile(request_handler, x, y, zoom)

    def get_local_tile(self, request_handler, x, y, zoom):
        tiledir = '/%d/%d/%d.png' % (zoom, x, y)
        try:
            with file(self.tilepath + tiledir) as f:
                image = f.read()
        except IOError:
            return False
        # some special remote tile handlers copied from the tangogps source
        if self.tileurl in ('maps-for-free', 'openaerial'):
            request_handler.write_header(content_type='image/jpeg',
                                         use_cache=1)
        else:
            request_handler.write_header(content_type='image/png',
                                         use_cache=1)
        request_handler.wfile.write(image)
        return True

    def get_remote_tile_url(self, x, y, zoom):
        # some special remote tile handlers copied from the tangogps source
        if self.tileurl == 'maps-for-free':
            return ('http://maps-for-free.com/layer/relief/' +
                        'z%d/row%d/%d_%d-%d.jpg' % (zoom, y, zoom, x, y))
        elif self.tileurl == 'openaerial':
            return ('http://tile.openaerialmap.org/tiles/1.0.0/' +
                        'openaerialmap-900913/%d/%d/%d.jpg' % (zoom, x, y))
        else:
            if self.zoom_last:
                return self.tileurl % (x, y, zoom)
            else:
                return self.tileurl % (zoom, x, y)

    def redirect_to_remote_tile(self, request_handler, x, y, zoom):
        request_handler.send_response(301)
        request_handler.send_header('Location',
                                    self.get_remote_tile_url(x, y, zoom))
        request_handler.end_headers()

    def send_remote_tile(self, request_handler, x, y, zoom):
        url = self.get_remote_tile_url(x, y, zoom)
        print("Fetchind %s..." % url)
        f = urllib2.urlopen(url)
        # XXX use write_header
        request_handler.send_response(200)
        request_handler.send_header('Content-type',
                                    f.info().get('Content-type'))
        # XXX Use real time (could be time-consuming)
        request_handler.send_header('Last-Modified',
                                    'Thu, 01 Jan 1970 00:00:00 GMT')
        request_handler.end_headers()
        shutil.copyfileobj(f, request_handler.wfile)

    @staticmethod
    def parse_tilerepos(repostring):
        if repostring.startswith('['):
            repostring = repostring[1:-1].split(',')
        else:
            repostring = repostring.split('\n')

        repos = []
        try:
            for repo in repostring:
                (title, url, path, zoom_last) = repo.strip().split('|')
                repos += [TileRepo(title, url, path, zoom_last != '0')]
        except Exception:
            if len(repos) == 0:
                repos = [TileRepo('OSM',
                                  'http://tile.openstreetmap.org/%d/%d/%d.png',
                                  None, False)]
        return repos


class ThreadingHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
    daemon_threads = True


# XXX The caching used here for articles and map tiles assumes that content
# never changes. You have to empty the browser's cache to get a new version
# from disk.


def main():
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: %s <data directory> [<port> [<tile repository string>]]"
                % sys.argv[0])
        sys.exit(1)

    data_dir = sys.argv[1]
    if not os.path.exists(data_dir):
        print("Data directory %s not found." % data_dir)
        sys.exit(1)

    port = (int(sys.argv[2]) if len(sys.argv) >= 3 else 8080)
    repostring = (sys.argv[3] if len(sys.argv) >= 4 else '')

    global tangogps_tilerepos
    tangogps_tilerepos = TileRepo.parse_tilerepos(repostring)
    print "Using map tile repositories " + str([x.title
                                                for x in tangogps_tilerepos])

    global gps_handler
    gps_handler = GPSHandler()

    global storage
    if config['storage'] == 'datafile':
        print "Using datafile storage."
        from datafile_storage import DatafileStorage
        storage = DatafileStorage()
        storage.storage_init_read(data_dir + '/titles.idx',
                                  data_dir + '/coordinates.idx',
                                  data_dir + '/wikipedia_%02d.dat',
                                  data_dir + '/metadata.txt')
    else:
        print "Unknown storage %s." % (config['storage'])
        sys.exit(1)

    try:
        server = ThreadingHTTPServer(('', port), EvopediaHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()
