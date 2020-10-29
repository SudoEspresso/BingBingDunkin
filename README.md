# BingBingDunkin
BingBingDunkin' automates searching using Bing as well as the daily quizes.

# Usage
`git clone https://github.com/SudoEspresso/BingBingDunkin.git`

`pip3 install -r requirements.txt`

_NOTE: BingBingDunkin.py ONLY works with the firefox selenium driver_
- Click [here](https://github.com/mozilla/geckodriver/releases) to get the latest release of mozilla's web-driver
  - Choose the appropriate one for your computers architecture
  - Once downloaded extract the binary and inside the `BingBingDunkin` folder 
    - Go into `BingBingDunkin.py` and change `GECKO_DRIVER` variable at the top of the file to be the name of what you just extracted

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
  
# Emailing

This program has the option to email you the results when it finishes so you don't need to check on it. I suggest using [MailGun](mailgun.com) it is free and is much better and easier than using a personal account.

1. First make an account
1. Verify your email ( They will ask for a phone number )
1. Go to Sending -> Overview -> Click on the domain
1. On the right hand side you will see "Authorized Recipients" enter all the recipients you want. ( They will need to verify each email )
1. Click SMTP
- Go into BingBingDunkin.py and change the following 
  - `EMAIL_SENDER_ADDRESS` to be your MailGun email address
  - `EMAIL_SENDER_PASSWORD` the password given under the email address
  - `EMAIL_RECEIVERS` a list of email addresses you want to send the report to ( They must be verified )
  - DO NOT change the port of the SMTP server
  
### Gmail Tips
The emails will most likely be sent to spam in your Gmail inbox.
Follow [this article](https://www.lifewire.com/how-to-whitelist-a-sender-or-domain-in-gmail-1172106) to force the emails to be not marked as spam.
  
# Tips
- You can automate this process to run daily by setting a cron job (if on Linux) or by creating a scheduled task (if on Windows)
  
  
