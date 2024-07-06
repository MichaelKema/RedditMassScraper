# RedditScraper
A Reddit Mass Scraper

Step-by-Step Installation Guide

1. Clone the GitHub Repository
First, clone your GitHub repository containing(Put the text below in the terminal) 

git clone https://github.com/your-username/reddit-mass-scraper.git
cd reddit-mass-scraper

2. Install Python
Ensure Python 3.x is installed on your system. You can check the Python version with in your terminal:

python --version

3.Install pip

If pip is not installed with Python, install it using your package manager or by following the instructions on pip.pypa.io.

4. Install Required Python Packages
Navigate to the project directory and install the required Python packages using pip and the requirements.txt file:

Type this into the termial:

cd reddit-mass-scraper
pip install -r requirements.txt


5. Set Up Reddit API Credentials

You need a reddit account for this program to work

You will require a reddit  client id and client secret

You can go to this link to learn how to get it: https://www.geeksforgeeks.org/how-to-get-client_id-and-client_secret-for-python-reddit-api-registration/#

  I. Go Login or create a reddit account if you need one

  II. Go to https://www.reddit.com/prefs/apps/

  III. Go the the bottom where it says ("are you a developer? create an app)

  IV. Enter a name for the app

  V. Select anyo of the three wehter it be web app, installed app, or script

  VI. fill the redirect url with local host like http://localhost:8080/ or anything else you use

  VII. The  line of letter and numbers under the personal use script is your client ID

  VIII. The random string of letter and numbers after the word secret is your Client Secret

 You might have to click edit under developed applications to see it


It will download the comments and written posts as csv files
