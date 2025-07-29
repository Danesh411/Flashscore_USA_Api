def soccer_extract(event_url, data_elements):
    import requests
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor, as_completed

    result_list = []
    venue_id_to_match = {}
    match_data = []
    venue_ids = []

    headers = {
        'x-fsign': 'SW9D1eZo',
    }

    for data_element in data_elements:
            country = data_element.xpath('.//span[contains(@class, "__countryName")]//text()').get()
            league = data_element.xpath('.//div[@class="event__titleBox"]//strong/text()').get()
            matches = data_element.xpath('.//div[contains(@class, "event__match") and not(contains(@class, "event__match--static"))]').getall()

            for match_idx in range(len(matches)):
                result_dict = {}

                product_page_id = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//a[contains(@class, 'eventRowLink')]/@aria-describedby"
                ).get()

                home_team = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'homeParticipant')]//text()"
                ).getall()
                home_team_score = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//span[contains(@class, 'score--home')]//text()"
                ).get()
                home_team_logo = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'homeParticipant')]/img/@src"
                ).get()

                away_team = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'awayParticipant')]//text()"
                ).getall()
                away_team_score = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//span[contains(@class, 'score--away')]//text()"
                ).get()
                away_team_logo = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'awayParticipant')]/img/@src"
                ).get()

                league_time = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'event__time')]//text()"
                ).get()
                status = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//div[contains(@class, 'event__stage')]//text()"
                ).getall()
                is_live = data_element.xpath(
                    f"(.//div[contains(@class, 'event__match') and not(contains(@class, 'event__match--static'))])[{match_idx + 1}]"
                    "//a[contains(@class, 'wcl-badgeLiveBet')]/@data-testid"
                ).get('N/A')
                is_live = 'animated' in is_live

                if not (home_team and away_team):
                    continue  # Skip incomplete matches

                venue_id = product_page_id.split("_")[-1] if product_page_id else None
                if not venue_id:
                    continue

                if not league_time and "".join(status):
                    status1 = "Finished" if "Final" in "".join(status) else "".join(status)
                elif league_time:
                    status1 = "Upcoming"
                elif is_live:
                    status1 = "Live"
                    status = (" ".join(status)).split(" ")[0] if "in" not in "".join(status) else " ".join(status)
                else:
                    status1 = None

                # Build partial result
                result_dict.update({
                    "link": event_url,
                    "sport": "soccer",
                    "country_name": country,
                    "league_name": league,
                    "status": status1,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "start_time": ("".join(league_time)).split(" ")[0] if league_time else None,
                    "team_1_name": " ".join(home_team) if "@" in home_team else "".join(home_team).strip(),
                    "team_2_name": " ".join(away_team) if "@" in away_team else "".join(away_team).strip(),
                    "team_1_score": home_team_score if "-" not in home_team_score else None,
                    "team_2_score": away_team_score if "-" not in away_team_score else None,
                    "team_1_Inning/quater_wise_score": None,
                    "team_2_Inning/quater_wise_score": None,
                    "livematchstate": status.strip() if is_live == True else None,
                    "team_1_logo": home_team_logo,
                    "team_2_logo": away_team_logo,
                    "venue_id": venue_id  # will be replaced later
                })

                match_data.append(result_dict)
                venue_ids.append(venue_id)
                venue_id_to_match[venue_id] = result_dict


    # === Fetch all venue data in parallel using ThreadPoolExecutor ===
    def fetch_venue(venue_id):
        url = f'https://global.flashscore.ninja/130/x/feed/df_sui_1_{venue_id}'
        try:
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                text = response.text
                if "÷VEN¬MIV÷" in text:
                    return venue_id, text.split("÷VEN¬MIV÷")[-1].split("¬")[0]
            return venue_id, ''
        except Exception:
            return venue_id, ''

    # Use ThreadPool for concurrent fetching
    with ThreadPoolExecutor(max_workers=100) as executor:  # Adjust max_workers as needed
        future_to_vid = {executor.submit(fetch_venue, vid): vid for vid in venue_ids}
        for future in as_completed(future_to_vid):
            vid, venue_name = future.result()
            match = venue_id_to_match[vid]
            match["venue"] = venue_name if venue_name else None
            del match["venue_id"]  # clean up
            result_list.append(match)

    return result_list