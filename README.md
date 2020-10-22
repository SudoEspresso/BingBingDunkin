# BingBingDunkin
BingBingDunkin' automates searching using Bing as well as the daily quizes.

# Usage
`git clone https://github.com/SudoEspresso/BingBingDunkin.git`

`pip3 install -r requirements.txt`

- Click [here](https://github.com/mozilla/geckodriver/releases) to get the latest release of mozilla's web-driver
  - Choose the appropriate one for your computers architecture
  - Once downloaded extract the binary and inside `BingBingDunkin.py` set the full path to the binary

- Modify credentials.ini to have the emails and passwords for each account
  - Make sure to follow the naming scheme for each set of credentials 
  
  ```
  [DEFAULT]
  email1=
  password1= 
  email2=
  password2= 
  ...
  email11=
  password11=
  ```
  
- Run it!
  - `python3 BingBingDunkin.py`
  
# Tips
- You can automate this process to run daily by setting a cron job (if on Linux) or by creating a scheduled task (if on Windows)
  
  
