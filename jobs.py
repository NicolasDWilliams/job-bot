#!/usr/bin/env python3
# jobs.py
# Main script
import os

import gspread
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# FIXME: Change back to production spreadsheet key
# SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
SPREADSHEET_KEY = os.getenv("DEV_SPREADSHEET_KEY")

SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")

gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
spreadsheet = gc.open_by_key(SPREADSHEET_KEY)


class JobPosting:
    """Class to contain information relating to job postings."""

    def __init__(self, title, company, url):
        self._title = title
        self._company = company
        self._url = url

    def spreadsheet_format(self):
        return [self._title, self._company, self._url]


# Acquire company webpages from google sheet configuration tab
# {"company":.., "url":.., "selector":..}
def acquire_webpages():
    # TODO: Implement this function
    config_ws = spreadsheet.worksheet("Configuration")
    companies = config_ws.get_all_records()
    return companies


# Returns a dictionary of lists of JobPostings parsed from each company website
# Keys are disciplines
def acquire_job_postings(company_dict_list):
    jobs = {
        "Animation": [],
        "Art": [],
        "Audio": [],
        "Design": [],
        "Production": [],
        "Programming": [],
        "Misc": [],
    }

    for c in company_dict_list:
        # Acquire html text of company career page
        webpage_html = requests.get(c["url"]).text
        # TODO: Smaller function here.
        webpage_jobs = parse_jobs_page(webpage_html, c["selector"])

        # Append jobs to aggreggated list
        for jt in filter_jobs(webpage_jobs):
            discipline = categorize_job(jt)
            jobs[discipline].append(JobPosting(jt, c["company"], c["url"]))

    return jobs


def parse_jobs_page(html_text, selector):
    # TODO Implement this function
    soup = BeautifulSoup(html_text, "html.parser")

    # Identify all jobs posted on company site
    job_titles = [entry.string.strip() for entry in soup.select(selector)]
    return job_titles


# Filters out irrelevant job postings such as senior positions
def filter_jobs(job_title_list):
    excluded_keywords = [
        "director",
        "executive",
        "lead",
        "manager",
        "principal",
        "senior",
    ]

    filtered_list = []

    for title in job_title_list:
        if not any(kw in title.lower() for kw in excluded_keywords):
            filtered_list.append(title)

    return filtered_list


def categorize_job(job_title):
    # NOTE: Ordered to avoid false positives (e.g. "design" in "sound designer")
    discipline_keywords = {
        "Production": ["producer", "project manager", "product manager", "production"],
        "Animation": ["animator", "rigger", "rigging"],
        "Art": ["artist"],
        "Audio": ["sound designer", "composer", "sound", "audio", "sfx"],
        "Design": ["designer"],
        "Programming": [
            "coder",
            "developer",
            "engineer",
            "engineering",
            "programmer",
            "programming",
        ],
    }

    for discipline, keywords in discipline_keywords.items():
        if any(kw in job_title.lower() for kw in keywords):  # Any keywords in job title
            return discipline

    # Doesn't match any disciplines
    return "Misc"


def update_job_sheet(worksheet_name, updated_jobs):
    if not updated_jobs:
        print(f"Jobs for {worksheet_name} is empty. Skipping..")
        return

    ws = spreadsheet.worksheet(worksheet_name)
    last_row_num = len(updated_jobs) + 1  # Header offset
    print(f"Last row number: {last_row_num}")
    ws.update(f"A2:C{last_row_num}", [j.spreadsheet_format() for j in updated_jobs])


##############################################################################
################################# SCRIPT BODY ################################
##############################################################################
if __name__ == "__main__":
    # Acquire webpages
    company_dicts = acquire_webpages()

    # Get job postings from webpages
    all_jobs = acquire_job_postings(company_dicts)

    for k in all_jobs.keys():
        update_job_sheet(k, all_jobs[k])

    # Update spreadsheet with postings
