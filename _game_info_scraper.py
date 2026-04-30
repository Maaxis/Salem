# Page scraper that formats game-related information for tinyurl.com/aliasorgdatabase, via ndimtools

import re
from datetime import datetime
import json
import ndimtools


def scrape_forum(url, driver):
	match = re.search(r'(?:ndimforums\.com/)?([^/]+)', url)
	if match:
		subdomain = match.group(1).strip()
	else:
		subdomain = url.strip()
	target_url = f"http://www.ndimforums.com/{subdomain}/"
	print(f"--- scraping {target_url} ---")
	forum = ndimtools.Forum(subdomain=subdomain, driver=driver)
	try:
		wall_data = ndimtools.get_mem_wall(forum)
		page_title = ndimtools.get_page_title(forum)
		last_post = ndimtools.get_latest_post(forum).isoformat()
		return json.dumps({
			"wall"      : wall_data,
			"page_title": page_title,
			"url"       : target_url,
			"last_post" : last_post
		})
	except Exception as e:
		return json.dumps({"error": f"Failed to scrape {target_url}: {str(e)}"})


def get_season_name(data):
	# based on page title
	try:
		if ":" in data['page_title']:
			# get portion after series name
			season_name = data['page_title'].split(":")[1].strip()
		else:
			season_name = data['page_title'].strip()
		return season_name
	except Exception:
		return " "


def get_season_number(data):
	# try page title
	match = re.search(r'(\d+)', data.get('page_title', ''))
	if match:
		return match.group(1)
	# try url
	match = re.search(r'(\d+)', data.get('url', ''))
	if match:
		return match.group(1)
	# else, return 1
	return "1"


def get_series_name(data):
	try:
		page_title = data['page_title'].strip()
		if ":" in data['page_title']:
			# get portion before season name
			page_title = data['page_title'].split(":")[0].strip()
		# ignore numbers and roman numerals
		return re.sub(r'\s+([0-9]+|[IVXLCDM]+)$', '', page_title, flags=re.IGNORECASE).strip()
	except Exception:
		return " "


def get_season_date(date_str):
	# e.g. [24.4] Winter 2024
	# convert to datetime
	dt = datetime.fromisoformat(date_str)
	month = dt.month
	year = dt.year
	if month in [12, 1, 2]:  # dec, jan, feb
		season_name = "Winter"
		season_id = 4
		# if jan or feb, season started last year, so subtract 1 year
		display_year = year - 1 if month in [1, 2] else year
	elif 3 <= month <= 5:  # mar, apr, may
		season_name = "Spring"
		season_id = 1
		display_year = year
	elif 6 <= month <= 8:  # june, july, aug
		season_name = "Summer"
		season_id = 2
		display_year = year
	else:  # sept, oct, nov
		season_name = "Fall"
		season_id = 3
		display_year = year
	# format string
	short_year = str(display_year)[-2:]
	return f"[{short_year}.{season_id}] {season_name} {display_year}"


def construct_row(alias, player, series, season, season_name, url, placement, cast_size, start_date):
	# score = "=(1-([@Placement]/[@[  ]]))*1000"
	hyperlink = f"=HYPERLINK(\"http://ndimforums.com/{url}\",\"{season_name}\")"
	sep = ";"
	return f"{alias.strip()}{sep}{player.strip()}{sep}{series.strip()}{sep}{series.strip()} {season.strip()}{sep}{hyperlink}{sep}{placement}{sep}/{sep}{cast_size}{sep}{start_date.strip()}"


def get_game(url, driver):
	data = json.loads(scrape_forum(url, driver))
	series = get_series_name(data)
	season = get_season_number(data)
	season_name = get_season_name(data)
	start_date = get_season_date(data['last_post'])
	cast_size = len(data['wall'])
	for index, item in enumerate(data['wall']):
		alias = item[0]
		player = " "
		placement = index + 1
		print(construct_row(alias, player, series, season, season_name, url, placement, cast_size, start_date))


if __name__ == '__main__':
	driver = ndimtools.start_driver()
	# games = ["rusticsurvivor7", "rusticsurvivor8", "rusticsurvivor9", "survivortwisted7", "survivortwisted8", "rusticsurvivor5", "survivortwisted6"]
	games = ['vicecity', 'kingdomhearts', 'southpark']
	for game in games:
		get_game(game, driver)
