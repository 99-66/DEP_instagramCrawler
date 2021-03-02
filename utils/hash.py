import hashlib


def generator_chash(article_comment: dict, _id: str) -> hashlib.md5:
    """
    댓글 hash 를 생성하여 반환한다
    다음 문자열을 합친 후 sha256 hash 값을 생성하여 반환한다
    _id + created_at + userId + content[:10]
    """
    sha256 = hashlib.new('sha256')
    hash_str = f'{_id}' \
               f'{article_comment["publishedAtTimestamp"]}' \
               f'{article_comment["userName"]}' \
               f'{article_comment["contentText"][:10]}'
    sha256.update(hash_str.encode())

    return sha256.hexdigest()
