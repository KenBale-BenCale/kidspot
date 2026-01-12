#!/bin/bash

echo "Setting up key packages for kidspot.\n" 

# setup.sh
echo "\nInstalling Python and i2c packages.\n"
sudo apt update && sudo apt install -y python3-venv python3-pip i2c-tools

# Create virtual environment
echo "\nInstalling and activating virtual environment.\n"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "\nInstalling all packages listed in requirements .txt. \n"
pip install --upgrade pip
pip install -r requirements.txt

# Enable Raspotify (assumes /etc/default/raspotify configured)
echo "\n Starting Raspotify \n"
sudo systemctl enable raspotify
sudo systemctl restart raspotify

echo "Setup complete. Activate the virtualenv with 'source venv/bin/activate'"
