import datetime
import logging
import os
import tempfile
import json
import random

from pathlib import Path
from time import perf_counter as timer
from openai import OpenAI

from pypdf_strreplace import main_func
from util.cvpartner import CvPartner
from util.open_ai import MyOpenAI
from util.slack import MySlack
from util.util import get_aws_logger

OpenAI_API_KEY = os.environ["OPENAI_API_KEY"]
slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_app_token = os.environ["SLACK_APP_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
assistant_ID = os.environ["OPENAI_ASSISTANT_ID"]

handled_cvs_filename = "handled.json"

# cv_partner_api_key = os.environ['CV_PARTNER_API_KEY']
cv_partner_api_key = "9bda65e4e89aae1142372158b5950c35"
cv_output_path = tempfile.TemporaryDirectory()

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

logger = get_aws_logger("evaluate_cvs")

logger.info("Starting to evaluate CVs")

def check_signle_cv(email_adr) -> str:
    logger.info(f"checking CV for user {email_adr}")
    all_users = cv_partner.get_users()
    user = all_users.get(email_adr, None)
    if user:
        check_cv(email_adr, user)
        return "ok"
    else:
        return "nok"

start_time = timer()
openai_client = OpenAI()
slack = MySlack(slack_bot_token, slack_app_token, slack_signing_secret, check_signle_cv, logger)

handled_cvs = {}

if os.path.exists(handled_cvs_filename):
    handled_cvs_json = Path(handled_cvs_filename).read_text()
    if handled_cvs_json:
        data = json.loads(handled_cvs_json)
        if bool(data):
            for email, date in data.items():
                handled_cvs[email] = datetime.datetime.fromisoformat(date)


cv_partner = CvPartner(cv_partner_api_key, logger, cv_output_path.name)

users = cv_partner.get_users()

my_open_ai = MyOpenAI(assistant_ID)

def check_cv(email_adr, cv_user):
    logger.info(f"checking CV for user {cv_user.name}")
    cv_filename = cv_partner.download_cv(cv_user.name, cv_user.user_id, cv_user.cv_id)
    patched_cv_filename = f"{cv_output_path.name}/konsulenten{random.randint(1, 9999)}.patched.pdf"
    main_func(cv_filename, patched_cv_filename, [(r"\d\s?\d\s?\d\s?\d\s?\d\s?\d\s?\d\s?\d", "00000000 "), (r"\S+@jpro.no","trash@jpro.no"), (cv_user.name,"Konsulenten")], "")
    result = my_open_ai.evaluate_cv(patched_cv_filename)

    slack.send_message(email_adr, result)

    handled_cvs[email_adr] = datetime.datetime.now()
    os.remove(cv_filename)
    os.remove(patched_cv_filename)

for email, user in users.items():
    if email in handled_cvs:
        cv_updated_at = user.updated_at
        last_checked_at = handled_cvs[email]
        if cv_updated_at <= last_checked_at:
            continue
        check_cv(email, user)
    else:
        check_cv(email, user)

with open(handled_cvs_filename, "w") as outfile:
    string = json.dumps(handled_cvs, indent=4, default=datetime.datetime.isoformat)
    outfile.writelines(string)

logger.info("Done with initial scan. All users that didn't have a scan before, or have updated their CV should have now. Going into normal run mode")

slack.start_listen_mode()
