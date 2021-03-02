import os
import platform
import time
from datetime import datetime, timedelta
from operator import itemgetter
from random import uniform

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

import config
from utils.emoji_text import strip_emoji
from utils.proxy import RandProxy
from utils.user_agent import random_user_agent


class InstagramCrawler:
    """
    인스타그램 크롤링을 위한 클래스
    크롤링 날짜 기준으로 최대 30일 이내의 포스트 정보를 가져온다
    """
    def __init__(self, username: str = None):
        self.proxy = RandProxy()
        self.user = username
        self.base_url = config.BASE_URL
        self._driver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
        self.MAX_CRAWL_DATE = 30
        self.CRAWL_DATE = config.CRAWL_DATE

    def url(self) -> str:
        """
        인스타그램의 유저 페이지 주소를 반환한다
        :return:
        """
        return self.base_url.format(username=self.user)

    def driver(self, hide=True) -> webdriver.Chrome:
        """
        Selenium Driver를 반환한다
        :param hide: browser의 숨김여부를 설정한다
        :return: webdriver Instance
        """
        path = self._driver_path
        proxies = self.proxy.get()

        drivers = {
            'darwin': 'chromedriver_mac',
            'linux': 'chromedriver_linux',
            'windows': 'chromedriver_windows.exe'
        }
        # O/S에 따라서 driver 파일의 경로를 설정한다
        path = os.path.join(path, drivers[platform.system().lower()])

        chrome_options = webdriver.ChromeOptions()
        if hide:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
        # Settings User-Agent
        chrome_options.add_argument(f'user-agent={random_user_agent()}')
        # Settings Proxy
        chrome_options.add_argument(f'--proxy-server={proxies["protocol"]}://{proxies["ip"]}:{proxies["port"]}')
        chrome_options.add_argument(f'"--proxy-auth={proxies["user"]}:{proxies["password"]}"')
        chrome_options.add_argument('lang=ko_KR')

        return webdriver.Chrome(path, chrome_options=chrome_options)

    @staticmethod
    def popup_check_and_close(driver: webdriver.Chrome) -> None:
        """
        인스타그램 페이지 하단에 로그인 팝업을 확인 후 클릭하여 없앤다
        :param driver: selenium webdriver instance
        :return: None
        """
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        if soup.select_one('button.dCJp8.afkep.xqRnw'):
            driver.find_element_by_css_selector('button.dCJp8.afkep.xqRnw').click()

    @staticmethod
    def select_first_post(driver: webdriver.Chrome) -> None:
        """
        인스타그램의 첫번째 포스트를 클릭하여 페이지를 연다
        페이지를 연 다음에, 강제적으로 1 ~ 1.5sec 사이의 딜레이를 준다
        :param driver: selenium webdriver instance
        :return: None
        """
        first = driver.find_element_by_css_selector('div._9AhH0')
        first.click()

        try:
            # 포스트의 오른쪽 본문 내용의 Tag가 로드될 때 까지 기다린다.
            # 최대 30초까지 기다리며, 이전에 완료된 경우에는 바로 넘어간다
            WebDriverWait(driver, 30).until(
                expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'div.C4VMK > span'))
            )
        except TimeoutException:
            raise TimeoutException('select_first_post(): Timed out waiting for page to load')
        else:
            time.sleep(uniform(1, 1.5))
            return None

    def parse_user_info(self, driver: webdriver.Chrome) -> dict:
        """
        인스타그램 페이지의 유저 정보를 파싱하여 반환한다
        :param driver: selenium webdriver instance
        :return: user page info(dict)
        """
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 인증배지 여부를 파싱한다
        if soup.select_one('span.mrEK_.Szr5J.coreSpriteVerifiedBadge'):
            verified_badge = True
        else:
            verified_badge = False
        # 포스트 수, 팔로워, 팔로잉 수를 파싱한다
        count_info_li = soup.select_one('ul.k9GMp').find_all('li')
        post_count = count_info_li[0].find('span').get_text(strip=True).replace(',', '')
        follower = count_info_li[1].find('span')['title'].replace(',', '')
        follow = count_info_li[2].find('span').get_text(strip=True).replace(',', '')

        # 유저 설명 부분을 파싱한다
        # 첫줄의 bold 라인과 아닌 부분을 나누어 파싱하여 합친다
        try:
            title = soup.select_one('div.-vDIg > h1').get_text(strip=True)
        except (AttributeError, TypeError):
            title = ''
        try:
            description = soup.select_one('div.-vDIg > span').get_text()
        except AttributeError:
            description = ''

        if title or description:
            user_description = f'{title}\n{description}'
        else:
            user_description = ''

        # 크롤링 시간을 설정한다
        crawlAt = self.CRAWL_DATE.strftime('%Y-%m-%d %H:%M:%S')
        crawlAtTimestamp = int(time.mktime(datetime.strptime(crawlAt, "%Y-%m-%d %H:%M:%S").timetuple()))

        return {
            '_id': self.user,
            'userName': self.user,
            'postCount': post_count,
            'followerCount': follower,
            'followingCount': follow,
            'userDescription': user_description,
            'VerifiedBadge': verified_badge,
            'crawlAtTimestamp': crawlAtTimestamp,
            'crawlAt': crawlAt
        }

    def daily_user_info(self, page_info: dict) -> dict:
        """
        인스타그램의 유저 정보를 매일 저장하기 위해 날짜 필드를 추가하여 반환한다
        :param page_info: 파싱한 인스타그램 유저 정보이다
        :return: 날짜를 추가한 인스타그램 유저정보이다
        """
        daily_page_info = page_info.copy()
        # 읽기 쉬운 날짜를 저장한다
        publishedAt = self.CRAWL_DATE.strftime('%Y-%m-%d %H:%M:%S')
        daily_page_info['publishedAt'] = publishedAt
        # 날짜를 타임스탬프 형식으로 저장한다
        publishedAtTimestamp = int(time.mktime(datetime.strptime(publishedAt, "%Y-%m-%d %H:%M:%S").timetuple()))
        daily_page_info['publishedAtTimestamp'] = publishedAtTimestamp
        # 인덱스 id 필드를 날짜를 추가하여 변경한다
        today_to_str = self.CRAWL_DATE.strftime('%Y-%m-%d')
        daily_page_info['_id'] = f'{today_to_str}_{daily_page_info["_id"]}'

        # 크롤링 시간 필드는 사용하지 않으므로 삭제한다
        del daily_page_info['crawlAt']
        del daily_page_info['crawlAtTimestamp']

        return daily_page_info

    def parse_content(self, driver: webdriver.Chrome) -> dict:
        """
        인스타그램의 포스트 내용과 댓글을 파싱하여 정보를 반환한다
        :param driver: selenium webdriver instance
        :return: post and comment data(dict)
        """
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 포스트 본문 내용을 파싱한다
        try:
            content = soup.select_one('div.C4VMK > span').get_text()
        except:
            content = ''
        else:
            # 본문 내용에 포함된 emoji를 제거한다
            content = strip_emoji(content)

        # 포스트의 댓글 내용들을 파싱한다
        comments = []
        try:
            comment_list = soup.select('div.C4VMK')
        except:
            pass
        else:
            for comment in comment_list:
                try:
                    writer = comment.find('a', {'class': 'FPmhX notranslate TlrDj'}).get_text(strip=True)
                except (AttributeError, TypeError):
                    continue

                # 댓글 작성자가 포스트 주인이 아닌 경우에만 정보를 파싱한다
                if not writer == self.user:
                    commenter = writer
                    comment_text = comment.find('span').get_text()
                    comment_date = comment.find('time', {'class': 'FH9sR Nzb55'})['datetime'][:19].replace('T', ' ')
                    publishedAtTimestamp = int(
                        time.mktime(datetime.strptime(comment_date, "%Y-%m-%d %H:%M:%S").timetuple()))
                    comments.append({
                        'username': commenter,
                        'commentText': comment_text,
                        'publishedAt': comment_date,
                        'publishedAtTimestamp': publishedAtTimestamp
                    })

        # 해쉬태그 정보를 파싱한다
        unclean_hashtags_list = soup.select('div.C4VMK > span > a.xil3i')
        hashtags = [tags.get_text(strip=True).replace('#', '') for tags in unclean_hashtags_list]

        # 포스트 작성시간을 파싱한다
        date = soup.select_one('time._1o9PC.Nzb55')['datetime'][:19].replace('T', ' ')
        # 포스트 작성시간이 MAX_CRAWL_DATE(30일) 이내인 것만 파싱한다
        x_days_ago = (self.CRAWL_DATE - timedelta(days=self.MAX_CRAWL_DATE)).strftime("%Y-%m-%d %H:%M:%S")

        date_timestamp = int(time.mktime(datetime.strptime(date, "%Y-%m-%d %H:%M:%S").timetuple()))
        x_days_ago_timestamp = int(time.mktime(datetime.strptime(x_days_ago, "%Y-%m-%d %H:%M:%S").timetuple()))

        if date_timestamp < x_days_ago_timestamp:
            raise ValueError('post created at over 30 days')

        # 포스트의 좋아요 수를 파싱한다
        try:
            like = soup.select_one('div.Nm9Fw > button > span').get_text()
        except AttributeError:
            # 동영상의 경우 '조회' 를 선택하여야 좋아요 개수가 보인다
            try:
                show_like = driver.find_element_by_css_selector('div.HbPOm._9Ytll > span.vcOH2')
                show_like.click()
                try:
                    show_like_count = WebDriverWait(driver, 15).until(
                        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'div.vJRqr > span'))
                    )
                except TimeoutException:
                    raise TimeoutException('parse_content(): content like parsed timed out')
            except:
                like = 0
            else:
                like = show_like_count.text.replace(',', '')
                try:
                    like_on_load = WebDriverWait(driver, 15).until(
                        expected_conditions.presence_of_element_located((By.CLASS_NAME, 'QhbhU'))
                    )
                except TimeoutException:
                    raise TimeoutException('parse_content(): like load to closed timed out')
                else:
                    like_on_load.click()

        else:
            like = like.replace(',', '')

        # 크롤링 시간을 설정한다
        crawlAt = self.CRAWL_DATE.strftime('%Y-%m-%d %H:%M:%S')
        crawlAtTimestamp = int(time.mktime(datetime.strptime(crawlAt, "%Y-%m-%d %H:%M:%S").timetuple()))

        # 댓글을 작성 시간순으로 정렬한다
        comments.sort(key=itemgetter('publishedAt'), reverse=True)

        data = {
            '_id': f'{self.user}_{date_timestamp}',
            'userName': self.user,
            'contentText': content,
            'publishedAtTimestamp': date_timestamp,
            'publishedAt': date,
            'crawlAtTimestamp': crawlAtTimestamp,
            'crawlAt': crawlAt,
            'likeCount': like,
            'hashtags': hashtags,
            'comments': comments
        }

        return data

    @staticmethod
    def next_page(driver: webdriver.Chrome) -> None:
        """
        포스트 크롤링 완료된 경우, 다음 페이지로 넘기기 위한 함수
        :param driver: selenium webdriver instance
        :return: None
        """
        # 다음 페이지로 넘아가기 위해, 페이지 넘기기 위치를 클릭한다
        try:
            right = driver.find_element_by_css_selector('a._65Bje.coreSpriteRightPaginationArrow')
        except NoSuchElementException:
            try:
                WebDriverWait(driver, 15).until(
                    expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'div.Igw0E > button.wpO6b'))
                )
            except TimeoutException:
                raise TimeoutException('next_page(): Timed out waiting for close button to load')
            else:
                # 열려 있는 포스트를 닫는다
                driver.find_element_by_css_selector('div.Igw0E > button.wpO6b').click()
                # 포스트 리스트를 가져와서 '추천 계정' 다음 항목의 포스트를 선택하여 오픈한다
                post_list = driver.find_elements_by_css_selector('div._9AhH0')
                if len(post_list) >= 9:
                    post_list[9].click()
                else:
                    raise EOFError(f'next post is None. post count is: {len(post_list)}')
        else:
            right.click()

        try:
            # 다음 포스트의 본문 Tag가 로드될 때까지 기다린다
            WebDriverWait(driver, 15).until(
                expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'div.C4VMK > span'))
            )
        except TimeoutException:
            raise TimeoutException('next_page(): Timed out waiting for page to load')
        else:
            time.sleep(uniform(0.3, 1))
            return None

    @staticmethod
    def page_available(html: webdriver.Chrome.page_source) -> bool:
        """
        인스타그램 유저의 페이지가 크롤링 할 수 있는지 확인한다
        * 비공개 또는 페이지를 찾을 수 없는 경우를 확인한다
        :return: bool
        """
        soup = BeautifulSoup(html, 'lxml')

        # 페이지를 찾을 수 없는 경우
        if soup.select_one('div.error-container'):
            return False
        # 비공개 계정인 경우
        elif soup.select_one('div.VIsJD'):
            return False
        # 게시물 없음인 경우
        elif soup.select_one('div.FuWoR.-wdIA.A2kdl'):
            return False
        else:
            return True
