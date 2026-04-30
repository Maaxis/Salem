# Selenium-based API for ndimforums.com. Most functions require a user account with password stored in secret.py
import re
import traceback
from selenium.common import NoSuchElementException
from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import asyncio
import datetime
import time
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich import print

browser_lock = asyncio.Lock()


def return_password(subdomain):
	from db.secret import passwords
	from base64 import b64decode
	pw = b64decode(passwords.get(subdomain))
	return pw.decode('utf-8')


class Forum:
	def __init__(self, subdomain: str, users: list['User'] = None, bot: 'Bot' = None, driver=None):
		self.subdomain = subdomain
		# we can pass in an existing driver to navigate between different forums. otherwise, start driver
		self.driver = driver
		if driver is None:
			self.driver = start_driver()
		self.url = "http://ndimforums.com/" + subdomain
		self.users = users
		self.bot = bot


class Post:
	def __init__(self, title=None, author=None, date=None, url=None, time=None, content=None):
		self.title = title
		self.author = author
		self.date = date
		self.url = url
		self.time = time
		self.content = content


class User:
	def __init__(self, subdomain: str, _id: int = None, username: str = None, password: str = None,
	             masks: list['Mask'] = None, avatar: str = None, display_name: str = None, group: 'Group' = None):
		self.subdomain = subdomain
		self.id = _id  # id is not required since we can also premake the object for preregistering
		self.username = username
		self.password = password
		self.masks = masks
		self.avatar = avatar
		self.group = group
		self.display_name = display_name


class Mask:
	def __init__(self):
		pass


class Group:
	def __init__(self):
		pass


class Bot(User):
	def __init__(self, subdomain: str, username: str, posts_per_page: int = 15):
		super().__init__(subdomain=subdomain, username=username, password=self.return_password(subdomain))
		self.posts_per_page = posts_per_page

	def return_password(self, subdomain):
		from db.secret import passwords
		from base64 import b64decode
		pw = b64decode(passwords.get(subdomain))
		return pw.decode('utf-8')


def start_driver():
	chrome_options = Options()
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--use-gl=desktop')
	chrome_options.add_argument('--disable-dev-shm-usage')
	# chrome_options.add_argument('--headless')
	# chrome_options.add_argument("--remote-debugging-port=9222")
	chrome_options.add_argument('user-data-dir=G:\\Code Projects\\PyCharmProjects\\Newo-2025\\selenium1')
	# IMPORTANT: user-data-dir must be provided for login to be maintained between restarts
	# when first starting the bot, manually log in to the bot account from the Chrome browser
	chrome_options.add_argument("--log-level=3")
	chrome_options.add_argument("--disable-logging")
	chrome_options.add_argument("--disable-gpu")
	# chrome_options.add_experimental_option("detach", True)
	driver = webdriver.Chrome(options=chrome_options)
	driver.get('https://www.google.com')
	driver.implicitly_wait(1)
	return driver


def quit_driver(driver):
	if driver:
		driver.quit()
		driver = None


def setup():  # use this for manual first-time logins
	start_driver()


def get_mem_wall(forum):
	try:
		results = _get_mem_wall(forum, 2)
		if len(results) == 0:
			results = _get_mem_wall(forum, 1)
	except Exception:
		traceback.print_exc()
	return results


def _get_mem_wall(forum, type=1):
	# There are two common types of memory walls on NDIM games, we have separate methods for each
	# type 1 = no movement on hover (HTML)
	# type 2 = name follows cursor on hover (JavaScript)
	results = []
	driver = forum.driver
	driver.get(forum.url)
	wait = WebDriverWait(driver, 5)
	if type == 1:
		# html based
		containers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "middle")))
		for item in containers:
			try:
				children = item.find_elements(By.XPATH, "./div")
				if len(children) >= 2:
					name = children[0].get_attribute("textContent").strip()
					placement = children[1].get_attribute("textContent").strip()
					results.append((name, placement))
			except Exception as e:
				traceback.print_exc()
	elif type == 2:
		# javascript based, get from page source
		page_source = driver.page_source
		pattern = r"wall\(\s*\d+\s*,\s*\d+\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'([^']*)'"
		matches = re.findall(pattern, page_source)
		results = matches
	# print(results)
	return results


def get_page_title(forum):
	driver = forum.driver
	driver.get(forum.url)
	title = driver.title
	return title


def get_latest_post(forum):
	# returns the first Last Post date it sees
	driver = forum.driver
	driver.get(forum.url)
	element = driver.find_element(By.CLASS_NAME, "lastpost")
	# get all text, split into lines, and take the last one
	raw_text = element.text
	lines = raw_text.split('\n')
	date_string = lines[-1].strip().replace('"', '')
	#print(date_string)  # Output: 28th Jan 2024 3:34:24 PM
	time = parse_time(date_string)
	return time


def parse_time(unformatted_time):
	"""Provide a time string from NDIM, returns a datetime object"""
	# TODO: make compatible for all time settings
	# Examples of acceptable inputs:
	# 5th Apr 2026 9:00:43 PM
	# Sunday 5th April 2026, 9:00:43 PM
	# 04/05/2026 21:00:43 (assumes MM/DD/YYYY)
	# Relative times don't work
	months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
	          'November', 'December']
	months_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
	time = unformatted_time
	# time1 = "5th Apr 2026 9:00:43 PM"
	# time2 = "Sunday 5th April 2026, 9:00:43 PM"
	# time3 = "04/05/2026 21:00:43"
	num_month = 0
	if "day" in unformatted_time:  # ignore mention of Sunday, remove comma
		time = unformatted_time.split("day ")[1]
		time = time.replace(",", "")
	# time1 = "5th Apr 2026 9:00:43 PM"
	# time2 = "5th April 2026 9:00:43 PM"
	# time3 = "04/05/2026 21:00:43"
	for month in months:
		if month in time:
			num_month = (months.index(month)) + 1
	for month in months_short:
		if month in time:
			num_month = (months_short.index(month)) + 1
	if "/" not in time:
		elements = time.split(" ")
		# day = ["5th", "Apr", "2026", "9:00:43", "PM"]
		day = elements[0].replace('th', '').replace('st', '').replace('nd', '').replace('rd', '')
		month = str(num_month)
		year = elements[2]
	else:  # for MM/DD/YYYY
		date = time.split(" ")[0]
		date = date.split("/")
		month = int(date[0])
		day = int(date[1])
		year = int(date[2])
	time = time.split(":")
	hour = time[0].split(" ")[-1]
	minute = time[1]
	second = time[2].split(" ")[0]
	if "PM" in time[2]:
		if hour == "12":
			hour = hour
		else:
			hour = str(int(hour) + 12)
	else:
		hour = hour
	full_time = str(year) + "-" + str(month) + "-" + str(day) + " " + str(hour) + ":" + str(minute) + ":" + str(second)
	datetime_obj = datetime.datetime.strptime(full_time, '%Y-%m-%d %H:%M:%S')
	return datetime_obj


def login(forum, user, admin=False):
	driver = forum.driver
	if admin:
		driver.get(forum.url + '/Admin/admincp.asp')
	else:
		driver.get(forum.url + '/login.asp')
	# username_box = driver.find_element(By.NAME, "username")
	pw_box = driver.find_element(By.NAME, "pwd")
	button = driver.find_element(By.XPATH, "//input[@value='login']")
	# username_box.send_keys("Newo")
	pw = return_password(subdomain=forum.subdomain)
	pw_box.send_keys(pw)
	driver.execute_script("arguments[0].click();", button)


def navigate_forum(forum: Forum, forum_id):
	driver = forum.driver
	url = f"ndimforums.com/{forum.subdomain}/forum.asp?forumid={forum_id}"
	driver.get(url)


def make_thread(forum: Forum, forum_id: int, thread_title: str, post_content: str, thread_description: str = "",
                locked: bool = False,
                pinned: bool = False,
                poll: bool = False, poll_question: str = "", poll_options: [str] = None,
                poll_num_of_votes: int = 0):
	#TODO: set up polls
	driver = forum.driver
	driver.get(forum.url + '/newthread.asp?forumid=' + str(forum_id))
	title_box = driver.find_element(By.XPATH,
	                                "//*[@id=\"sendform\"]/div/table/tbody/tr[2]/td/table/tbody/tr[1]/td[2]/input")
	description_box = driver.find_element(By.XPATH,
	                                      "//*[@id=\"sendform\"]/div/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]/input")
	post_box = driver.find_element(By.ID, "fullreply")
	title_box.send_keys(thread_title)
	description_box.send_keys(thread_description)
	post_box.send_keys(post_content)
	if locked:
		lock = driver.find_element(By.XPATH,
		                           "//*[@id=\"sendform\"]/div/table/tbody/tr[2]/td/table/tbody/tr["
		                           "6]/td/table/tbody/tr/td[1]/input")
		lock.send_keys(Keys.ENTER)
		lock.click()
	if pinned:
		pin = driver.find_element(By.XPATH,
		                          "//*[@id=\"sendform\"]/div/table/tbody/tr[2]/td/table/tbody/tr["
		                          "6]/td/table/tbody/tr/td[2]/input")
		pin.send_keys(Keys.ENTER)
		pin.click()
	create = driver.find_element(By.XPATH, "//*[@id=\"sendform\"]/div/table/tbody/tr[2]/td/table/tbody/tr[7]/td/input")
	create.click()


def read_thread(forum, thread_id):
	# use old_read_thread
	pass


def navigate_thread(forum, thread_id):
	driver = forum.driver
	url = f"ndimforums.com/{forum.subdomain}/thread.asp?threadid={thread_id}"
	driver.get(url)


def make_post(forum, post_content, thread_id=None):
	driver = forum.driver
	thread = f"ndimforums.com/{forum.subdomain}/thread.asp?threadid={thread_id}"
	if (thread_id) and (thread not in driver.current_url):
		navigate_thread(forum, thread_id)
	text_box = driver.find_element(By.ID, "fastreply")
	reply_button = driver.find_element(By.CSS_SELECTOR, '.buttonstyle:nth-child(3)')
	text_box.send_keys(post_content)
	reply_button.send_keys(Keys.ENTER)


def read_post(forum, thread_id, post_num, pp):
	# use get_post_content_with_time
	pass


###---ADMIN CP---###

def goto_admin_cp(forum):
	if '/Admin/admincp.asp' not in forum.driver.current_url:
		try:
			login(forum, forum.bot, admin=True)
		except:
			forum.driver.get(f"http://www.ndimforums.com/{forum.subdomain}/Admin/admincp.asp")
	time.sleep(1)


def navigate_in_admin_cp(forum, menu_item):
	goto_admin_cp(forum)
	driver = forum.driver
	driver.switch_to.default_content()
	link = driver.find_element(By.LINK_TEXT, menu_item)
	link.send_keys(Keys.ENTER)
	iframe = driver.find_elements(By.TAG_NAME, 'iframe')[0]
	driver.switch_to.frame(iframe)


def navigate_news_fader(forum: Forum):
	navigate_in_admin_cp(forum, "News Fader")


async def set_news_fader(forum: Forum, news_fader: str = None):
	async with browser_lock:
		try:
			navigate_news_fader(forum)
			driver = forum.driver
			attempts = 0
			while attempts < 5:
				try:
					time.sleep(0.5)
					textbox = driver.find_element(By.NAME, "fadertext")
					break
				except:
					navigate_news_fader(forum)
					attempts = attempts + 1
			if news_fader:
				textbox.clear()
				textbox.send_keys(news_fader)
				on_button = driver.find_element(By.CSS_SELECTOR, 'input[name="donoff"][value="on"]')
				on_button.click()
			else:
				off_button = driver.find_element(By.CSS_SELECTOR, 'input[name="donoff"][value="off"]')
				off_button.click()
			save = driver.find_element(By.CSS_SELECTOR, 'input.buttonstyle[value="Save"]')
			save.click()
		except Exception as e:
			print(f"Error changing news fader: {e}")


def navigate_masks(forum: Forum):
	navigate_in_admin_cp(forum, "Forum Masks")


def create_mask(forum, mask_name, dictionary):
	"""
	Create a mask in the forum.

	Args:
		forum (Forum): The forum object.
		mask_name (str): The name of the mask to be created.
		dictionary (dict): A dictionary containing the mask values.

	Returns:
		None
	"""
	navigate_masks(forum)
	driver = forum.driver
	# test_dict = {
	#	"my forum": "",
	#	"subforum": "",
	#	"another forum": "v",
	#	"unique name": "vrc"
	# }
	# v = view, r = reply, c = create
	add_button = driver.find_element(By.XPATH, "//*[@id=\"admin0\"]/table/tbody/tr[2]/td/table/tbody/tr/td/input")
	add_button.click()
	textbox = driver.find_element(By.CLASS_NAME, "textboxstyle")
	textbox.send_keys(mask_name)
	save = driver.find_element(By.XPATH, "//*[@id=\"admin0\"]/table/tbody/tr[9]/td/table/tbody/tr/td/input[4]")
	save.click()
	edit_mask(forum, mask_name, dictionary)


def edit_mask(forum, mask_name, dictionary, overwrite=False):
	"""
	Edits a mask on the forum.

	Parameters:
		forum (Forum): The forum object.
		mask_name (str): The name of the mask to edit.
		dictionary (dict): A dictionary containing the forum titles as keys and the desired permissions as values.
			Each value is a string containing the characters v, r, and/or c.
			V = View
			R = Reply
			C = Create Thread
			If a character appears in the string, that permission will be granted.
			e.g. "vr" will grant "View" and "Reply" permissions, but not "Create Thread."
			A blank string will grant no permissions.
		overwrite (bool, optional): Whether to overwrite and remove existing permissions not specified by the dictionary keys.
			If set to True, this is equivalent to setting all other permissions as blank/not allowed for any forum not specified in the dictionary.
			Defaults to False.
	"""
	# from masks page, locate and click edit button
	driver = forum.driver
	navigate_masks(forum)
	n = 1
	while True:
		try:
			ele = driver.find_element(By.XPATH,
			                          f"//*[@id=\"admin0\"]/table/tbody/tr[4]/td/table/tbody/tr[{n}]/td[1]").text
			if ele == mask_name:
				break
		except NoSuchElementException:
			print("mask not found")
			break
		n = n + 1
	edit_button = driver.find_element(By.XPATH,
	                                  f"//*[@id=\"admin0\"]/table/tbody/tr[4]/td/table/tbody/tr[{n}]/td[2]/input")
	edit_button.click()
	# test_dict = {
	#	"my forum": "",
	#	"subforum": "",
	#	"another forum": "v",
	#	"unique name": "vrc"
	# }
	# v = view, r = reply, c = create
	# from edit mask page, locate elements
	n = 1
	j = 6
	headers = []
	driver.implicitly_wait(0.1)
	while True:
		try:
			ele = driver.find_element(By.XPATH,
			                          f"// *[ @ id = \"admin0\"] / table / tbody / tr[{j}] / td / table / tbody / tr[{n}] / td[1]").text
			headers.append(ele.lower())
			n = n + 1
		except NoSuchElementException:
			if n == 1:
				break
			else:
				n = 1
				j = j + 2
	driver.implicitly_wait(1)
	# select masks
	for forum_title in headers:
		for key, value in dictionary.items():
			if key in forum_title:  # this has a definition
				red_cell = "rgba(153, 51, 51, 1)"
				n = headers.index(forum_title) + 1
				row = str(n)
				view = driver.find_element(By.XPATH, f"// *[ @ id = \"readcell{row}\"]")
				reply = driver.find_element(By.XPATH, f"// *[ @ id = \"replycell{row}\"]")
				create = driver.find_element(By.XPATH, f"// *[ @ id = \"createcell{row}\"]")
				if "v" in value:  # view should be green
					if view.value_of_css_property("background-color") == red_cell:  # but is red
						view.click()  # so toggle
				else:  # view should be red
					if view.value_of_css_property("background-color") != red_cell:  # but is green
						view.click()  # so toggle
				if "r" in value:
					if reply.value_of_css_property("background-color") == red_cell:
						reply.click()
				else:
					if reply.value_of_css_property("background-color") != red_cell:
						reply.click()
				if "c" in value:
					if create.value_of_css_property("background-color") == red_cell:
						create.click()
				else:
					if create.value_of_css_property("background-color") != red_cell:
						create.click()
			elif overwrite and key not in forum_title:
				pass  # TODO: finish overwrite masks
	save = driver.find_element(By.CLASS_NAME, "buttonstyle")
	save.click()


def read_mask(forum, user):
	pass


def navigate_groups(forum):
	navigate_in_admin_cp(forum, "Group Manager")


def create_group(forum):
	pass


def edit_group(forum):
	pass


def read_group(forum):
	pass


def preregister_member(forum):
	# pre-make the User class
	navigate_in_admin_cp(forum, "Pre-register Member")




def return_user_obj(_id: int):
	pass


def navigate_edit_member(forum):
	navigate_in_admin_cp(forum, "Member Editor")


def search_member(forum):
	navigate_edit_member(forum)


def edit_member_username():
	pass


def edit_member_display_name():
	pass


def edit_member_password():
	pass


def edit_member_group(forum: Forum, user: User, group: Group):
	pass


def edit_member_masks(forum: Forum, user: User, masks: list[Mask]):
	pass


def edit_member_email():
	pass


def edit_member_title():
	pass


def edit_member_post_count():
	pass


def edit_member_avatar():
	pass


def edit_member_signature():
	pass


def navigate_edit_filters(forum):
	navigate_in_admin_cp(forum, "Word Filters")


def export_filters(forum):
	navigate_edit_filters(forum)
	driver = forum.driver
	time.sleep(1)
	with open("filters.txt", "a+") as file:
		i = 1
		inarow = 0
		# TODO: better way of determining if we've reached the end
		# If filters are deleted at all, the try block will fail because i is not incremented
		# For now we assume if we fail 5 in a row we're at the end, but this can't be guaranteed
		while i < 1000:
			try:
				word = driver.find_element(By.NAME, f"wordtoedit{i}").get_attribute("value")
				print(word)
				replacement = driver.find_element(By.NAME, f"changesto{i}").get_attribute("value")
				print(replacement)
				file.write(word + "," + replacement + "\n")
				i = i + 1
				inarow = 0
			except:
				print(f"no {i}")
				i = i + 1
				inarow = inarow + 1
				if inarow > 5:
					print("Assumed end")
					break
				else:
					continue
	print("Done export")


def clear_filters(forum):
	navigate_edit_filters(forum)
	driver = forum.driver
	delete_buttons = driver.find_elements(By.XPATH, "//input[@type='Button'][@value='Delete']")
	for delete_button in delete_buttons:
		delete_button.click()
		WebDriverWait(driver, 10).until(EC.alert_is_present())
		alert = Alert(driver)
		alert.accept()
	print("Done clear")


def add_filter(word_to_change, new_word, forum, mode=0):
	# mode 0 is Full Word Only, mode 1 is Containing Word
	goto_admin_cp(forum)
	driver = forum.driver
	if "Add Filters" not in driver.page_source:
		navigate_edit_filters(forum)
	text_boxes = driver.find_elements(By.XPATH, "//input[@type='text']")
	word1 = text_boxes[0]
	word1.clear()
	word1.send_keys(word_to_change)
	word2 = text_boxes[1]
	word2.clear()
	word2.send_keys(new_word)
	print(word_to_change + " -> " + new_word)
	button = driver.find_elements(By.XPATH, "//input[@type='Submit']")[0]
	selector = Select(driver.find_elements(By.CLASS_NAME, "selectstyle")[0])
	selector.select_by_value(str(mode))
	button.send_keys(Keys.ENTER)


def remove_filters(forum): # alias for clear_filters
	clear_filters(forum)


def add_filters(filter_dictionary: dict, forum: Forum, mode: int = 0):
	# filters should be in key value pairs
	for item in filter_dictionary:
		add_filter(item, filter_dictionary[item], forum, mode)


async def add_filters_from_file(forum, filename, delimiter):
	async with browser_lock:
		with open(filename) as file:
			for line in file:
				word_to_change = line.split(delimiter)[0].strip()
				filter = line.split(delimiter)[1].strip()
				add_filter(word_to_change, filter, forum)
				time.sleep(0.2)


def overwrite_filters():
	pass


def old_read_thread(url, driver, pp=50):  # posts per page must match bot's user account setting on the board
	# Exports posts from a thread to a file
	sep = "\t"
	time_list = []
	newfile = "{}.txt".format(
		datetime.datetime.now().strftime("%Y-%m-%d %H%M%S"))
	thread_id = input("thread id: ")
	print("Please wait...", flush=True)
	post_contents = []
	post_headers = []
	post_users = []
	for current_page in range(1, 100):
		driver.get("http://www.ndimforums.com/{0}/thread.asp?threadid={1}&pagenum={2}&pp={3}".format(url, thread_id,
		                                                                                             current_page,
		                                                                                             str(pp)))
		for post_num_this_page in range(1, pp + 1):
			try:
				if post_num_this_page == 1:
					this_user = driver.find_element(By.CSS_SELECTOR, ('.profile:nth-child(3) span')).text
				else:
					offset = post_num_this_page * 4 - 2
					this_user = driver.find_element(By.CSS_SELECTOR,
					                                (f'tr:nth-child({str(offset)}) .profile span')).text
				post_num_total = post_num_this_page + (pp * (current_page - 1))
				post_time_unformatted = driver.find_element(By.CSS_SELECTOR,
				                                            (f'#postheada{str(post_num_this_page)} > b')).text
				post_time_formatted = parse_time(post_time_unformatted)
				post_content = driver.find_element(By.ID, (f"post{post_num_this_page}")).text
				line = f"{this_user:<14}{str(post_time_formatted):<24}Post #{str(post_num_total):<8}{post_content}"
				post_users.append(this_user)
				time_list.append(post_time_formatted)
				post_headers.append(post_num_total)
				post_contents.append(post_content)
				with open(newfile, "a") as file:
					file.write(f"{this_user}{sep}{post_time_formatted}{sep}{post_num_total}{sep}{post_content}" + "\n")
				print(line, flush=True)
			except:
				old_read_thread(url, driver)
	return newfile


async def log_active_users(forum, filename="db/activity.log", sep="|"):
	# export from Active Users page to activity log
	ips = []
	async with browser_lock:
		dt = datetime.datetime
		driver = forum.driver
		driver.get(forum.url + '/activeuser.asp')
		current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
		arr = []
		i = 2
		while True:
			try:
				anon = False
				display_name = driver.find_element(By.CSS_SELECTOR,
				                                   f'.innertable tr:nth-child({i}) > .innercontent:nth-child(1)').text
				try:
					profile_url = driver.find_element(By.CSS_SELECTOR,
					                                  f'.innertable tr:nth-child({i}) > .innercontent:nth-child(1) a').get_attribute(
						'href')
					# print(profile_url)
					user_id = profile_url.split("=")[-1]
				except:
					user_id = "Guest"
				if display_name.startswith("*"):
					anon = True
					display_name = display_name.replace("*", "")
				last_action = driver.find_element(By.CSS_SELECTOR,
				                                  f'.innertable tr:nth-child({i}) > .innercontent:nth-child(2)').text
				last_activity = parse_time(driver.find_element(By.CSS_SELECTOR,
				                                               f'tr:nth-child({i}) > .innercontent:nth-child(3)').text).strftime(
					"%Y-%m-%d %H:%M:%S")
				ip_address = driver.find_element(By.CSS_SELECTOR,
				                                 f'tr:nth-child({i}) > .innercontent:nth-child(4)').text
				arr.append([current_time, display_name, last_action, last_activity, ip_address])
				ips.append(f"{user_id}{sep}{ip_address}")
				i += 1
				display_name = display_name.replace(sep, "")
				last_action = last_action.replace(sep, "")
				with open(filename, "a", encoding="utf-8", errors="replace") as file:
					file.write(
						f"{current_time}{sep}{display_name}{sep}{user_id}{sep}{last_action}{sep}{last_activity}{sep}{ip_address}{sep}{anon}\n")
			except NoSuchElementException:
				break
		f = '\n'.join(ips)
		with open("db/activity_last_update.log", "w+", encoding="utf-8", errors="replace") as file:
			file.write(f)
		print(f"[green]\\[{current_time}][/] [yellow]\\[ndimtools][/]: Activity log updated.")
	return ips


async def get_active_topics(forum, time_limit=120, mask=None):
	"""Navigate to Active Topics with an optional viewAs mask, and return all recent posts within the time limit."""
	async with browser_lock:
		driver = forum.driver
		if mask is None:
			driver.get(forum.url + '/activetopics.asp')
		else:
			driver.get(forum.url + f"/activetopics.asp?viewAs={mask}")
		i = 2
		n = 1
		posts = []
		while True:
			try:
				# TODO: these finders get finnicky between different boards, find something more reliable
				author = driver.find_element(By.CSS_SELECTOR,
				                             f"tr:nth-child({i}) > .forumbody{n}:nth-child(6) > .profile").text
				time = driver.find_element(By.CSS_SELECTOR, f"tr:nth-child({i}) > .forumbody{n}:nth-child(6)").text
				time = time.replace(author, "").strip()
				time_as_dt = parse_time(time)
				if time_as_dt < datetime.datetime.now() - datetime.timedelta(minutes=time_limit):
					break
				title = driver.find_element(By.CSS_SELECTOR, f"tr:nth-child({i}) > .forumbody{n}:nth-child(2) > a").text
				url = driver.find_element(By.CSS_SELECTOR,
				                          f"tr:nth-child({i}) > .forumbody{n}:nth-child(2) > a").get_attribute("href")
				url = url.split("&")[0]
				post = Post(title=title, author=author, time=time_as_dt, url=url)
				posts.append(post)
				if n == 1:
					n = 0
				elif n == 0:
					n = 1
				i += 1
			except Exception as e:
				traceback.print_exc()
				break
		return posts


async def get_post_content_with_time(forum, post):
	async with browser_lock:
		try:
			driver = forum.driver
			driver.get(post.url)
			i = 1
			while True:
				try:
					time_unformatted = driver.find_element(By.CSS_SELECTOR, f"#postheada{i} > b").text
					time = parse_time(time_unformatted)
					time_str = str(time)
					time_l = time_str.split(":")
					time_no_sec = ":".join([time_l[0], time_l[1]])
					post_time_str = str(post.time)
					post_time_l = post_time_str.split(":")
					post_time_no_sec = ":".join([post_time_l[0], post_time_l[1]])
					if time_no_sec.strip() == post_time_no_sec.strip():
						post.content = driver.find_element(By.ID, f"post{i}").text
						break
					i += 1  # TODO: breaks if it needs to go to next page
				except Exception as e:
					print(e)
					raise Exception
			return post
		except Exception as e:
			print(e)
			raise Exception


async def main():
	forum = Forum("survivalhorror7")
	print(get_mem_wall(forum))


if __name__ == "__main__":
	asyncio.run(main())
