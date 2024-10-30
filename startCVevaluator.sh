#!/bin/bash

cd /home/ubuntu/cv_evaluator || exit

# imports env variables CV_PARTNER_API_KEY, OPENAI_API_KEY,
# OPENAI_ASSISTANT_ID, SLACK_BOT_TOKEN. SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
source /etc/environment

source cv_evaluator/bin/activate && python3 cvevaluator.py


