import re
import emoji


def strip_emoji(text):
    # emoji 삭제
    new_text = re.sub(emoji.get_emoji_regexp(), r'', text)
    # emoji 로 되어있는 공백/띄어쓰기 없애기
    emoji_pattern = re.compile("["
                               u"\u2800"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r' ', new_text).strip()


def remove_emoji(string):
    # 첫번째 emoji 패턴으로 문장내 emoji 삭제
    NON_BMP_RE = re.compile(u"[^\U00000000-\U0000d7ff\U0000e000-\U0000ffff]", flags=re.UNICODE)
    rem_emoji_text = NON_BMP_RE.sub(r'', string)

    # 두번째 emoji 패턴으로 문장내 emoji 삭제
    emoji_pattern = re.compile("["
                               u"\u200d"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\u3030"
                               u"\ufe0f"
                               "]+", flags=re.UNICODE)

    return emoji_pattern.sub(r'', rem_emoji_text)


"""
find emoji pattern
for i in range(0x2600, 0x2B55):
    number = hex(i).replace('0x', '')
    emoji = f'\\u{number}'
    emoji_pattern = re.compile(f"[u{emoji}]+", flags=re.UNICODE)
    print(emoji,' : ', emoji_pattern.sub(r'', text))
"""