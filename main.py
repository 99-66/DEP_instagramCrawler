import time
import logging
from datetime import datetime
from functools import partial
from random import uniform
from multiprocessing import Pool

import pymongo.errors
import sentry_sdk
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from utils.logger import custom_logger, send_error
from utils.crawler import InstagramCrawler
from config import proc_numbers
from connector.connector import MongoDBConnector, RedisConnector

custom_logger = custom_logger()
logger = custom_logger.getLogger(__name__)
sentry_sdk.init("")


def main(overwrite: bool, username: str) -> None:
    """
    인스타그램의 유저 페이지를 크롤링한다
    :param overwrite: 포스트 정보를 저장할 때, 중복여부에 따라 크롤링을 종료한다
    :param username: 인스타그램 유저이름이다
    :return: None
    """
    redis_conn = RedisConnector()
    conn = MongoDBConnector().conn()
    user_collection = conn['']['']
    daily_user_collection = conn['']['']
    data_collection = conn['']['']

    crawler = InstagramCrawler(username)
    driver = crawler.driver()
    driver.get(crawler.url())

    # 인스타그램 유저의 페이지 정보를 크롤링한다
    try:
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'div._9AhH0'))
        )
    except TimeoutException as e:
        # page not-found, 비공개 계정등인 경우에는 로깅을 하지 않는다
        if crawler.page_available(driver.page_source):
            # 에러가 발생하는 경우, retry 를 위해 redis-logging
            logging.error(f'{username} Page GET: Timed out waiting for page to load')
            redis_conn.saved_error(username, repr(e))
            send_error(f'{username}: \n{repr(e)} main(): Timed out waiting for page to load')
        else:
            logging.info(f'{username}: Private user or page not found.')
        driver.close()
        driver.quit()
        return
    else:
        page_info = crawler.parse_user_info(driver)
        logging.info(page_info)

        # 최신 유저 정보를 저장한다
        user_collection.replace_one({'_id': page_info['_id']}, page_info, upsert=True)
        # 일짜별로 유저 정보를 저장한다
        daily_page_info = crawler.daily_user_info(page_info)
        daily_user_collection.replace_one({'_id': daily_page_info["_id"]}, daily_page_info, upsert=True)

        time.sleep(uniform(1, 1.5))

    # 인스타그램 페이지 하단에 로그인이 필요하다는 팝업을 닫는다
    # 이 팝업을 닫지 않는 경우, 첫번째 포스트 클릭 시 방해가 되어 에러가 발생하는 경우가 있다
    crawler.popup_check_and_close(driver)

    # 인스타그램 유저의 가장 최신의 포스트를 선택한다
    try:
        crawler.select_first_post(driver)
    except TimeoutException as e:
        # 에러가 발생하는 경우, retry 를 위해 redis-logging
        logging.error(f'{username}: {repr(e)}')
        redis_conn.saved_error(username, repr(e))
        send_error(f'{username}: \n{repr(e)}')
        driver.close()
        driver.quit()
        return
    while True:
        try:
            data = crawler.parse_content(driver)
        except ValueError:
            # 30일이 지난 포스트인 경우 'ValueError'를 발생시킨다
            # 다음 유저 정보의 크롤링을 위해 이번 유저의 크롤링 루프를 종료한다
            break
        except TimeoutException as e:
            # 에러가 발생하는 경우, retry 를 위해 redis-logging
            logging.error(f'{username}: {repr(e)}')
            redis_conn.saved_error(username, repr(e))
            send_error(f'{username}: \n{repr(e)}')
            break
        else:
            # 포스트 정보를 저장한다
            # 'overwrite' 가 True 라면, 30일 이내의 모든 포스트 정보를 중복여부에 상관없이 다시 저장한다
            # 'overwrite '가 False 라면, 30일 이내의 포스트를 크롤링 시에 이미 저장되어 있는 포스트가 있다면 크롤링을 중지한다
            if overwrite:
                data_collection.replace_one({'_id': data['_id']}, data, upsert=True)
            else:
                try:
                    pass
                    data_collection.insert_one(data)
                except pymongo.errors.DuplicateKeyError:
                    logging.warning(f'Duplicate document: key {data["_id"]}')
                    break

            logging.info(data)
            # 다음 포스트로 넘긴다
            try:
                crawler.next_page(driver)
            except NoSuchElementException as e:
                logging.error(f'{username}: {repr(e)}')
                redis_conn.saved_error(username, repr(e))
                send_error(f'{username}: \n{repr(e)}')
                driver.close()
                driver.quit()
                break
            except TimeoutException as e:
                # 에러가 발생하는 경우, retry 를 위해 redis-logging
                logging.error(f'{username}: {repr(e)}')
                redis_conn.saved_error(username, repr(e))
                break
            except EOFError as e:
                logging.warning(f'{username}: {repr(e)}')
                break

    driver.close()
    driver.quit()


if __name__ == '__main__':
    logging.info(f'## START: crawling....{datetime.now()}')
    start = time.time()

    pool = Pool(processes=proc_numbers)
    # main function 과 overwrite 여부를 설정한다
    func = partial(main, True)
    pool.map(func, MongoDBConnector().over_500_followers())

    end = time.time()
    logging.info(f'## END: crawling... time taken: {end - start}')
    send_error(f'main crawling end..time taken: {end - start}')
