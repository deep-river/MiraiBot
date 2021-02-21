import aiohttp
import lxml.html
import typing as T
import urllib.request
from urllib.parse import quote_plus
from mirai import Mirai, Group, GroupMessage, MessageChain, Image

sub_app = Mirai(f"mirai://localhost:8080/?authKey=0&qq=0")


@sub_app.receiver(GroupMessage)
async def find_pic(app: Mirai, group: Group, message: MessageChain):
    if '搜图' in message.toString() or '识图' in message.toString():
        image: T.Optional[Image] = message.getFirstComponent(Image)
        if image and image.url:
            await app.sendGroupMessage(group, await do_search(image.url))


async def do_search(url: str):
    # saucenao
    s_url = f'https://saucenao.com/search.php?url={url}'
    # ascii2d
    encoded_url = f'https://ascii2d.net/search/url/{url_encoder(url)}'

    s_info = await get_saucenao_detail(s_url)

    if s_info and percent_to_int(s_info[0]['Similarity']) > 0.7:
        msg = 'SauceNAO搜图结果：\n'
        for k, v in s_info[0].items():
            if k != 'Content':
                msg += f'{k}: {v}\n'
            else:
                msg += f'{v}\n'
        return msg.strip()
    else:
        page_url, info = await get_ascii2d_detail(encoded_url)
        if info:
            msg = 'ascii2d搜图结果：\n'
            for k, v in info[0].items():
                msg += f'{k}: {v}\n'
            msg += f'如以上内容不符，请尝试手动打开如下链接，并点选\"特徴検索\"以获取更多结果:\n {page_url}'
        else:
            msg = '未找到相似图片\n'
        return msg.strip()


async def get_saucenao_detail(s_url):
    async with aiohttp.client.request('GET', s_url) as resp:
        text = await resp.text(encoding='utf8')

    html_e: lxml.html.HtmlElement = lxml.html.fromstring(text)
    results = [
        {
            'Similarity': ''.join(
                r.xpath('.//div[@class="resultsimilarityinfo"]/text()')),
            'Title': ''.join(
                r.xpath('.//div[@class="resulttitle"]/descendant-or-self::text()')),
            'Content': '\n'.join(
                r.xpath('.//div[@class="resultcontentcolumn"]/descendant-or-self::text()')).replace(': \n', ': '),
            'URL': ''.join(
                r.xpath('.//div[@class="resultcontentcolumn"]/a[1]/attribute::href')),
        }
        for r in html_e.xpath('//div[@class="result"]/table[@class="resulttable"]')
    ]
    return results


# 百分数转为int
def percent_to_int(string):
    if string.endswith('%'):
        return float(string.rstrip("%")) / 100
    else:
        return float(string)


# async def shorten_img_url(url: str):
#     i_url = f'https://iqdb.org/?url={url}'
#     async with aiohttp.client.request('GET', i_url) as resp:
#         text = await resp.text(encoding='utf8')
#
#     html_e: lxml.html.HtmlElement = lxml.html.fromstring(text)
#     img_uri = html_e.xpath('//img[contains(attribute::src,"/thu/thu_")]/attribute::src')[0]
#     img_url = f'https://iqdb.org{img_uri}'
#     return img_url


async def get_ascii2d_detail(url):

    # The following functions won't work properly for god knows what reason
    # So here I'm using urllib.request instead of aiohttp

    # async with aiohttp.client.request('GET', url) as resp:
    #     print(resp.status)
    #     text = await resp.text(encoding='utf8')

    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url) as resp:
    #         text = await resp.text(encoding='utf8')

    async with urllib.request.urlopen(url) as resp:
        page_url = await resp.url
        text = await resp.read().decode()
    html_e: lxml.html.HtmlElement = lxml.html.fromstring(text)
    item_box = html_e.xpath('//div[@class="row item-box"][2]')
    if not item_box:
        results = []
        return results
    elements = item_box[0].xpath('.//h6/a')
    date, author = elements[0].xpath('./descendant-or-self::text()')[0], \
                      elements[1].xpath('./descendant-or-self::text()')[0]
    post_link, author_page = elements[0].xpath('./attribute::href')[0], elements[1].xpath('./attribute::href')[0]
    results = [
        {
            'Link': post_link,
            'Content': date,
            'Author': author
        }
    ]
    return page_url, results


def url_encoder(url):
    return quote_plus(url)
