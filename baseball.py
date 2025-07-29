def baseball_extract(event_url, data_elements):
    import requests
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor, as_completed

    result_list = []
    match_data = []
    venue_id_to_match = {}
    headers = {
        'x-fsign': 'SW9D1eZo',
    }

    for data_element in data_elements:
        country = data_element.xpath('.//span[contains(@class, "__countryName")]//text()').get()
        league = data_element.xpath('.//div[@class="event__titleBox"]//strong/text()').get()

        # Get only valid match rows (exclude static headers, etc.)
        match_rows = data_element.xpath('.//div[contains(@class, "event__match") and not(contains(@class, "event__match--static"))]')
        if not match_rows:
            continue

        for match_idx in range(len(match_rows)):
            result_dict = {}

            # Extract Product Page ID for this specific match
            product_page_id = match_rows[match_idx].xpath('.//a[contains(@class, "eventRowLink")]/@aria-describedby').get()
            if not product_page_id:
                continue
            venue_id = product_page_id.split("_")[-1]

            # Team names
            home_team = match_rows[match_idx].xpath('.//div[contains(@class, "event__participant--home")]//text()').getall()
            away_team = match_rows[match_idx].xpath('.//div[contains(@class, "event__participant--away")]//text()').getall()

            # Scores
            home_team_score = match_rows[match_idx].xpath('.//span[contains(@class, "event__score--home")]//text()').get()
            away_team_score = match_rows[match_idx].xpath('.//span[contains(@class, "event__score--away")]//text()').get()

            # Logos
            home_team_logo = match_rows[match_idx].xpath('.//img[contains(@class, "event__logo--home")]/@src').get()
            away_team_logo = match_rows[match_idx].xpath('.//img[contains(@class, "event__logo--away")]/@src').get()

            # Time & Status
            league_time = match_rows[match_idx].xpath('.//div[contains(@class, "event__time")]//text()').get()
            status = match_rows[match_idx].xpath('.//div[contains(@class, "event__stage")]//text()').getall()
            is_live_data = match_rows[match_idx].xpath('.//a[contains(@class, "wcl-badgeLiveBet")]/@data-testid').get('N/A')
            is_live = 'animated' in is_live_data

            if not (home_team and away_team):
                continue  # Skip incomplete matches

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
                "sport": "baseball",
                "country_name": country,
                "league_name": league,
                "status": status1,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "start_time": (league_time or "").strip().split(" ")[0] if league_time else None,
                "team_1_name": " ".join(home_team) if "@" in home_team else "".join(home_team).strip(),
                "team_2_name": " ".join(away_team) if "@" in away_team else "".join(away_team).strip(),
                "team_1_score": home_team_score if "-" not in home_team_score else None,
                "team_2_score": away_team_score if "-" not in away_team_score else None,
                "Team 1 Inning/quater wise score": None,
                "Team 2 Inning/quater wise score": None,
                "livematchstate": status.strip() if is_live == True else None,
                "team_1_logo": home_team_logo,
                "team_2_logo": away_team_logo,
                "venue_id": venue_id
            })

            match_data.append(result_dict)
            venue_id_to_match[venue_id] = result_dict

    # === Parallel venue fetching using ThreadPoolExecutor ===
    def fetch_venue(vid):
        url = f'https://global.flashscore.ninja/130/x/feed/df_sui_1_{vid}'
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                text = response.text
                if "÷VEN¬MIV÷" in text:
                    return vid, text.split("÷VEN¬MIV÷")[-1].split("¬")[0]
            return vid, ''
        except Exception:
            return vid, ''

    # Run concurrent requests
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_vid = {executor.submit(fetch_venue, m["venue_id"]): m for m in match_data}
        for future in as_completed(future_to_vid):
            vid, venue_name = future.result()
            match = future_to_vid[future]
            match["venue"] = venue_name if venue_name else None
            del match["venue_id"]  # cleanup
            result_list.append(match)

    return result_list