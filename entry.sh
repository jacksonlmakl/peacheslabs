#!/bin/bash
sudo nohup python3 auth.py > auth.log 2>&1 &
sudo nohup python3 auth_upload.py > upload.log 2>&1 &
sudo nohup python3 auth_app.py > app.log 2>&1 &
