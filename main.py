def main(category):
    import json
    import time, datetime
    from DrissionPage import ChromiumPage, ChromiumOptions
    from baseball import baseball_extract
    from basketball import baseketball_extract
    from football import football_extract
    from soccer import soccer_extract
    from parsel import Selector

    # st_tm = time.time()

    clo1 = ChromiumOptions().set_local_port(1279)
    clo2 = ChromiumOptions().set_local_port(1280)
    clo3 = ChromiumOptions().set_local_port(1281)
    clo4 = ChromiumOptions().set_local_port(1282)
    if category == "basketball":
        browser = ChromiumPage(clo1)
        tab = browser.latest_tab
    elif category == "baseball":
        browser = ChromiumPage(clo2)
        tab = browser.latest_tab
    elif category == "football":
        browser = ChromiumPage(clo3)
        tab = browser.latest_tab
    elif category == "soccer":
        browser = ChromiumPage(clo4)
        tab = browser.latest_tab
    else:
        return None
    event_url = f"https://www.flashscoreusa.com/{category}"
    tab.get(event_url)
    time.sleep(2)

    tab.run_js('''
            document.querySelectorAll('[data-testid="wcl-icon-action-navigation-arrow-down"]').forEach(el => {
                const clickable = el.closest('button, div, span');
                if (clickable && typeof clickable.click === 'function') {
                    clickable.click();
                }
            });
            ''')
    raw_html = tab.html

    selector = Selector(text=raw_html)
    league_header_divs = selector.xpath('//div[@data-testid="wcl-headerLeague"]')
    if league_header_divs:

        modified_tag_list = []
        full_html = selector.get()  # Get once to avoid repeated calls
        index_list = []

        for index, league_node in enumerate(league_header_divs):
            league_html = league_node.get()
            div_index = full_html.rfind(league_html)
            index_list.append(div_index)

            # Build modified tags for all except the last item
            if index < len(league_header_divs) - 1:
                next_league_html = league_header_divs[index + 1].get()
                next_div_index = full_html.rfind(next_league_html)
                modified_tag = '<div class="added-start-tag">' + full_html[div_index:next_div_index]
                modified_tag_list.append(modified_tag)

        modified_tag = '<div class="added-start-tag">' + selector.get()[index_list[-1]:] + '</div>'
        modified_tag_list.append(modified_tag)

        modified_html_data = '</div>'.join(modified_tag_list)

        new_selector = Selector(modified_html_data)

        data_elements = new_selector.xpath('//div[@class="added-start-tag"]')

        if category == "basketball":
            data_extract = baseketball_extract(event_url, data_elements)
        elif category == "baseball":
            data_extract = baseball_extract(event_url, data_elements)
        elif category == "football":
            data_extract = football_extract(event_url, data_elements)
        elif category == "soccer":
            data_extract = soccer_extract(event_url, data_elements)
        else:
            data_extract = "Something in category"
    else:
        data_extract = "No matches Available"

    tab.close()
    return data_extract

# if __name__ == '__main__':
#     category = "soccer"
#     category = "football"
#     category = "baseball"
    # category = "basketball"
    # st_time = time.time()
    # result = main(category)
    # print(json.dumps(result))
    # print(time.time() - st_time)
    # tab.close()