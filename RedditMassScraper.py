import praw
import csv
import os
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse



def check_reddit_credentials(client_id, client_secret, user_agent):
    auth = HTTPBasicAuth(client_id, client_secret)
    headers = {'User-Agent': user_agent}
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, headers=headers, data=data)
    
    if response.status_code == 200:
        return True
    else:
        return False


while True:
    client_id = input("Please enter your client id: ")
    client_secret = input("Please enter your client secret id: ")
    AgentInput = input("Please enter your reddit username: ")
    user_agent = "Extraction by: " + AgentInput
    if check_reddit_credentials(client_id, client_secret, user_agent):
        print("Credentials are valid.")
        reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)
        break
    else:
        print("Invalid credentials. Please check your client_id and client_secret.")


# downloads the images from reddit

def download_media(url, directory):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            # Parse the filename from the URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            filepath = os.path.join(directory, filename)
            # Write the media file to the directory
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download: {url}")
    except Exception as e:
        print(f"Error: {e}")




def UserScrape(username, limit):
    
    redditor = reddit.redditor(username)
    posts = []
    print(f"Posts by {username}:")

    image_directory = os.path.join(os.getcwd(), f"{username}_images")
    os.makedirs(image_directory, exist_ok=True)

    for submission in redditor.submissions.new(limit=limit):
        title_parts = submission.title.split(' - ', 1)
        if len(title_parts) > 1:
            cleaned_title = title_parts[1].strip()
        else:
            cleaned_title = title_parts[0].strip()
        posts.append({
        'Title': submission.title,
        'URL': submission.url,
        "created_utc": submission.created_utc,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "id": submission.id
           })
        if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4')):
            download_media(submission.url, image_directory)

    csv_file = f'{username}.csv'

# Write posts to CSV file
    if posts:  # Check if the posts list is not empty
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=posts[0].keys())
            writer.writeheader()
            for post in posts:
                writer.writerow(post)


def extract_user_comments_to_csv(username, limit):

    output_file = f'{username}_comments.csv'

    try:
        # Get the Redditor instance
        redditor = reddit.redditor(username)
        
        # Open CSV file for writing
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Comment ID','Comment URL' , 'Comment Body', 'Subreddit', 'Score'])  # Write header
            
            # Iterate through the comments
            for comment in redditor.comments.new(limit=limit):
                writer.writerow([comment.id,  f"https://www.reddit.com{comment.permalink}", comment.body.replace('\n', ' '), comment.subreddit.display_name, comment.score])
                print(f"Comment ID: {comment.id} written to {output_file}")
    
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to download media files


# Fetch top media from subreddit

def fetch_top_media(subreddit_name, limit, time_filter):
    subreddit = reddit.subreddit(subreddit_name)
    directory = os.path.join(os.getcwd(), subreddit_name)
    os.makedirs(directory, exist_ok=True)
    
    submissions = subreddit.top(limit=limit, time_filter=time_filter)
    posts = []
    for submission in submissions:
        posts.append({
            'Title': submission.title,
            'URL': submission.url,
            "created_utc": submission.created_utc,
            "score": submission.score,
            "num_comments": submission.num_comments,
            "id": submission.id
        })
        if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4')):
            download_media(submission.url, directory)

    csv_file = f'{subreddit_name}_posts.csv'

    if posts:
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=posts[0].keys())
            writer.writeheader()
            for post in posts:
                writer.writerow(post)
# Get subreddit name and limit from user
while True:
    print("Welcome to the RedditMassScraper")
    print("Do you want to Scrape A User or a Subreddit?")
    UserInput = input("User | Subreddit : " )
    UserInput = UserInput.lower()
    if UserInput == "user":
        try:
            while True:
                RedInput = input("Please enter a username (type cancel to cancel): ")
                if RedInput == "cancel":
                        break
                UserLimit = input("Please enter a limit (type cancel to cancel): ")
                if UserLimit == "cancel":
                    print("Going back to the beginning")
                    break
                UserScrape(RedInput, int(UserLimit))
                extract_user_comments_to_csv(RedInput, int(UserLimit))
        except:
            print("Invalid Username or Limit entered")
    elif UserInput == "subreddit":
        try:
            while True:
                SubInput = input("Please enter a subreddit (type cancel to cancel): ")
                if SubInput == "cancel":
                    print("Going back to the beginning")
                    break
                while True:
                    LimitInput = input("Please enter a limit (type cancel to cancel): ")
                    if LimitInput == "cancel":
                        print("Going back ")
                        break
                    while True:
                        TimeInput = (input("Please enter a the time period you want. The options are (all | hour | day | week | month | year) (type cancel to cancel): "))
                        if TimeInput == "cancel":
                            print("Going back")
                            break

                        fetch_top_media(SubInput, int(LimitInput), TimeInput)
                        break
        except:
                print("Error, incorrect subreddit input")
    
    elif UserInput == "exit":
        break
    else:
        print("Not a valid input, try again")



