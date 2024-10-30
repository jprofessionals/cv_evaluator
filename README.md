Setup:
```
sudo apt-get update
sudo apt-get upgrade
sudo apt -y install python3-pip
sudo apt install python3.12-venv
mkdir ~/cv_evaluator
cd ~/cv_evaluator
python3 -m venv cv_evaluator
source cv_evaluator/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

<copy files into ~/cv_evaluator>

sudo cp cvevaluator.service /etc/systemd/system/cvevaluator.service
sudo systemctl enable cvevaluator.service
sudo systemctl daemon-reload
sudo service cvevaluator start

```

add root crontab to restart the cvevaluator every night

```
sudo crontab -e
```
and add the line

01,03 * * * * /home/ubuntu/cv_evaluator/restart.sh

