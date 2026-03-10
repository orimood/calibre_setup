# -*- coding: utf-8 -*-

# Copyright 2024 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import
import json
import logging
import re
from datetime import datetime

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from .base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)


def getClass():
    return NovelFireNetAdapter


class NovelFireNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        # get storyId (slug) from url -- /book/{slug}
        m = re.match(r'/book/([^/]+)', self.parsedUrl.path)
        if m:
            self.story.setMetadata('storyId', m.group(1))

        # normalized story URL
        self._setURL('https://' + self.getSiteDomain() + '/book/' + self.story.getMetadata('storyId'))

        self.story.setMetadata('siteabbrev', 'nvlfr')

    @staticmethod
    def getSiteDomain():
        return 'novelfire.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['novelfire.net', 'www.novelfire.net']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://novelfire.net/book/some-novel-name https://novelfire.net/book/some-novel-name/chapter-1"

    def getSiteURLPattern(self):
        return r"https?://(?:www\.)?novelfire\.net/book/(?P<id>[^/]+)(/chapter-\d+)?/?$"

    @classmethod
    def get_section_url(cls, url):
        url = re.sub(r'^(https?://.*?/book/[^/]+)(/.*)?$', r'\1', url)
        return url

    def performLogin(self):
        """Log in to novelfire.net using email/password from config."""
        email = self.getConfig("username")
        password = self.getConfig("password")

        if not email or not password:
            return False

        # Fetch any page to get the CSRF token
        login_page_url = 'https://' + self.getSiteDomain() + '/home'
        data = self.get_request(login_page_url, usecache=False)
        soup = self.make_soup(data)

        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
        if not csrf_meta or not csrf_meta.get('content'):
            logger.warning("Could not find CSRF token for login")
            return False

        csrf_token = csrf_meta['content']

        # POST to /loginAjax
        login_url = 'https://' + self.getSiteDomain() + '/loginAjax'
        params = {
            'email': email,
            'password': password,
            'remember': '1',
            '_token': csrf_token,
        }

        logger.debug("Logging in to %s as %s" % (login_url, email))
        response = self.post_request(login_url, params)

        # Check login success - the AJAX endpoint returns JSON
        try:
            resp_data = json.loads(response)
            if resp_data.get('status') == 200:
                logger.debug("Login successful")
                return True
            else:
                logger.warning("Login failed: %s" % resp_data.get('message', 'Unknown error'))
                raise exceptions.FailedToLogin(
                    self.url, "Failed to login as %s" % email)
        except (json.JSONDecodeError, TypeError):
            # If it's not JSON, check if we got redirected to a logged-in page
            if 'logout' in response.lower() or 'account' in response.lower():
                logger.debug("Login appears successful (non-JSON response)")
                return True
            logger.warning("Login response was not JSON and doesn't appear successful")
            raise exceptions.FailedToLogin(
                self.url, "Failed to login as %s" % email)

    def before_get_urls_from_page(self, url, normalize):
        """Login before fetching library/account pages."""
        if '/account/' in url:
            self.performLogin()

    def get_urls_from_page(self, url, normalize):
        """
        Override to handle paginated library pages.
        Usage: fanficfare --list https://novelfire.net/account/library
        """
        # Only handle library/account pages specially
        if '/account/library' not in url:
            return super().get_urls_from_page(url, normalize)

        self.before_get_urls_from_page(url, normalize)

        novel_urls = []
        page_url = url
        # Ensure page parameter is present
        if '?' not in page_url:
            page_url += '?page=1'

        while page_url:
            logger.debug("Fetching library page: %s" % page_url)
            data = self.get_request(page_url, usecache=False)
            soup = self.make_soup(data)

            # Find all novel links on the page - they follow /book/{slug} pattern
            for a in soup.find_all('a', href=re.compile(r'^/book/[^/]+$')):
                novel_url = 'https://' + self.getSiteDomain() + a['href']
                if novel_url not in novel_urls:
                    novel_urls.append(novel_url)

            # Follow pagination
            page_url = None
            pagination = soup.find('ul', class_='pagination')
            if pagination:
                next_link = pagination.find('a', attrs={'rel': 'next'})
                if next_link and next_link.get('href'):
                    page_url = next_link['href']
                    if not page_url.startswith('http'):
                        page_url = 'https://' + self.getSiteDomain() + page_url

        logger.debug("Found %d novels in library" % len(novel_urls))
        return {'urllist': novel_urls}

    def extractChapterUrlsAndMetadata(self):
        url = self.url
        logger.debug("URL: " + url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        # Check for 404
        title_tag_check = soup.find('title')
        if title_tag_check and 'not found' in stripHTML(title_tag_check).lower():
            raise exceptions.StoryDoesNotExist(self.url)

        ## Title - <h1 class="novel-title">
        title_tag = soup.find('h1', class_='novel-title')
        if title_tag is None:
            title_tag = soup.find('h1')
        if title_tag:
            self.story.setMetadata('title', stripHTML(title_tag))

        ## Author - inside div.novel-info div.author a.property-item
        novel_info = soup.find('div', class_='novel-info')
        if novel_info:
            author_div = novel_info.find('div', class_='author')
            if author_div:
                author_links = author_div.find_all('a', class_='property-item')
                if author_links:
                    # First link is the English name
                    author_name = stripHTML(author_links[0])
                    self.story.setMetadata('author', author_name)
                    author_href = author_links[0].get('href', '')
                    if author_href:
                        author_id = author_href.rsplit('/', 1)[-1]
                        self.story.setMetadata('authorId', author_id)
                        self.story.setMetadata('authorUrl',
                                               'https://' + self.getSiteDomain() + author_href)

        ## Cover image - .fixed-img figure.cover img
        cover_img = soup.select_one('.fixed-img figure.cover img')
        if cover_img and cover_img.get('src'):
            self.setCoverImage(url, cover_img['src'])
        else:
            # Fallback: og:image meta tag
            og_img = soup.find('meta', attrs={'property': 'og:image'})
            if og_img and og_img.get('content'):
                self.setCoverImage(url, og_img['content'])

        ## Rating from JSON-LD AggregateRating
        for script_tag in soup.find_all('script', type='application/ld+json'):
            try:
                ld_data = json.loads(script_tag.string)
                if ld_data.get('@type') == 'AggregateRating':
                    self.story.setMetadata('rating', ld_data.get('ratingValue', ''))
                    break
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

        ## Status - inside div.header-stats
        header_stats = soup.find('div', class_='header-stats')
        if header_stats:
            # Status is in a <strong> tag next to <small>Status</small>
            for span in header_stats.find_all('span'):
                small = span.find('small')
                if small and stripHTML(small).lower() == 'status':
                    strong = span.find('strong')
                    if strong:
                        status_text = stripHTML(strong).strip().lower()
                        if status_text == 'completed':
                            self.story.setMetadata('status', 'Completed')
                        elif status_text in ('ongoing', 'in-progress'):
                            self.story.setMetadata('status', 'In-Progress')
                        elif status_text == 'hiatus':
                            self.story.setMetadata('status', 'Hiatus')
                        else:
                            self.story.setMetadata('status', stripHTML(strong).strip())
                    break

        ## Genres - div.categories ul li a.property-item
        categories = soup.find('div', class_='categories')
        if categories:
            for a in categories.find_all('a', class_='property-item'):
                self.story.addToList('genre', stripHTML(a))

        ## Tags
        tags_div = soup.find('div', class_='tags')
        if tags_div:
            for a in tags_div.find_all('a', class_='tag'):
                self.story.addToList('extratags', stripHTML(a))

        ## Description - div.summary div.content
        summary_div = soup.find('div', class_='summary')
        if summary_div:
            content_div = summary_div.find('div', class_='content')
            if content_div:
                # Remove the "Show More" expand button
                for expand in content_div.find_all('div', class_='expand'):
                    expand.extract()
                self.setDescription(url, content_div)

        ## Crawl chapter list (paginated)
        chapters_url = ('https://' + self.getSiteDomain() + '/book/'
                        + self.story.getMetadata('storyId') + '/chapters')
        self._crawl_chapters(chapters_url)

    def _crawl_chapters(self, url):
        """Crawl paginated chapter list pages."""
        logger.debug("Fetching chapter list: " + url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        chapter_list = soup.find('ul', class_='chapter-list')
        if not chapter_list:
            raise exceptions.FailedToDownload(
                "Could not find chapter list at %s" % url)

        for li in chapter_list.find_all('li', recursive=False):
            a = li.find('a')
            if not a or not a.get('href'):
                continue

            chapter_title = a.get('title', '')
            if not chapter_title:
                title_tag = a.find('strong', class_='chapter-title')
                chapter_title = stripHTML(title_tag) if title_tag else stripHTML(a)

            chapter_url = 'https://' + self.getSiteDomain() + a['href']

            # Parse date from <time class="chapter-update" datetime="...">
            time_tag = a.find('time', class_='chapter-update')
            chapter_date = None
            if time_tag and time_tag.get('datetime'):
                try:
                    chapter_date = datetime.strptime(
                        time_tag['datetime'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass

            self.add_chapter(chapter_title, chapter_url)

            # First chapter -> datePublished, keep updating dateUpdated
            if chapter_date:
                if self.num_chapters() == 1:
                    self.story.setMetadata('datePublished', chapter_date)
                self.story.setMetadata('dateUpdated', chapter_date)

        # Follow pagination - find next page link
        pagination = soup.find('ul', class_='pagination')
        if pagination:
            next_link = pagination.find('a', attrs={'rel': 'next'})
            if next_link and next_link.get('href'):
                self._crawl_chapters(next_link['href'])

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.find('div', id='content')

        if content is None:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s! Missing required element!" % url)

        # Remove ads (in case any are server-rendered)
        for ad in content.find_all('div', class_='nf-ads'):
            ad.extract()
        for ad in content.find_all('div', id=re.compile(r'^bg-ssp-')):
            ad.extract()
        for ad in content.find_all('div', id=re.compile(r'^pf-')):
            ad.extract()
        for ad in content.find_all('iframe'):
            ad.extract()
        for ad in content.find_all('script'):
            ad.extract()

        return self.utf8FromSoup(url, content)
