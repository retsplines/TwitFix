import youtube_dl
import textwrap
import twitter
import json
import re
import os
import urllib.parse
import urllib.request

pathregex = re.compile("\\w{1,15}\\/(status|statuses)\\/\\d{2,20}")
generate_embed_user_agents = [
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0",
    "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "TelegramBot (like TwitterBot)",
    "Mozilla/5.0 (compatible; January/1.0; +https://gitlab.insrt.uk/revolt/january)",
    "test"
]

# Read config from config.json
f = open("config.json")
config = json.load(f)
f.close()

# Empty dummy link cache
link_cache = {}

# If method is set to API or Hybrid, attempt to auth with the Twitter API
if config['config']['method'] in ('api', 'hybrid'):
    auth = twitter.oauth.OAuth(config['api']['access_token'], config['api']['access_secret'], config['api']['api_key'], config['api']['api_secret'])
    twitter_api = twitter.Twitter(auth=auth)

def lambda_handler(event, context):
    """
    Main Lambda event handler.
    """
    path = event['rawPath']
    user_agent = event['headers']['user-agent']

    # Lambda includes a prefix / in the path, so strip it out
    if path[0] == "/":
        path = path[1:]

    match = pathregex.search(path)
    if match is not None:
        twitter_url = path

        if match.start() == 0:
            twitter_url = "https://twitter.com/" + path

        if user_agent in generate_embed_user_agents:
            res = embed_video(twitter_url)
            return res

        else:
            print(" ➤ [ R ] Redirect to " + twitter_url)
            return redirect(twitter_url, 301)
    else:
        print('Invalid URL')

def render_template(name, **kwargs):
    """
    Render a template with the given name and arguments.
    """
    f = open(name)
    template_contents = f.read()
    for key, value in kwargs.items():
        template_contents = template_contents.replace("{{ " + key + " }}", value)
    f.close()
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': template_contents
    }
    
def redirect(url, code):
    return {
        'statusCode': code,
        'headers': {
            'Location': url,
            'Content-Type': 'text/html'
        },
        'body': '<html><body>Redirecting to <a href="' + url + '">' + url + '</a></body></html>'
    }

def embed_video(video_link):
    vnf = get_vnf_from_link_cache(video_link)
    if vnf == None:
        vnf = link_to_vnf(video_link)
        add_vnf_to_link_cache(video_link, vnf)
    return embed(video_link, vnf)

def video_info(url, tweet="", desc="", thumb="", uploader=""): # Return a dict of video info with default values
    vnf = {
        "tweet"         :tweet,
        "url"           :url,
        "description"   :desc,
        "thumbnail"     :thumb,
        "uploader"      :uploader
    }
    return vnf

def link_to_vnf_from_api(video_link):
    print(" ➤ [ + ] Attempting to download tweet info from Twitter API")
    twid = int(re.sub(r'\?.*$','',video_link.rsplit("/", 1)[-1])) # gets the tweet ID as a int from the passed url
    tweet = twitter_api.statuses.show(_id=twid, tweet_mode="extended")

    # Check to see if tweet has a video, if not, make the url passed to the VNF the first t.co link in the tweet
    if 'extended_entities' in tweet:
        if 'video_info' in tweet['extended_entities']['media'][0]:
            if tweet['extended_entities']['media'][0]['video_info']['variants'][-1]['content_type'] == "video/mp4":
                url = tweet['extended_entities']['media'][0]['video_info']['variants'][-1]['url']
                thumb = tweet['extended_entities']['media'][0]['media_url']
            else:
                url = tweet['extended_entities']['media'][0]['video_info']['variants'][-2]['url']
                thumb = tweet['extended_entities']['media'][0]['media_url']
        else:
            url = re.findall(r'(https?://[^\s]+)', tweet['full_text'])[0]
            thumb = "Non video link with url"
            print(" ➤ [ NV ] Non video tweet, but has a link: " + url)
    else:
        url = re.findall(r'(https?://[^\s]+)', tweet['full_text'])[0]
        thumb = "Non video link with url"
        print(" ➤ [ NV ] Non video tweet, but has a link: " + url)

    if len(tweet['full_text']) > 200:
        text = textwrap.shorten(tweet['full_text'], width=200, placeholder="...")
    else:
        text = tweet['full_text']

    vnf = video_info(url, video_link, text, thumb, tweet['user']['name'])
    return vnf

def link_to_vnf_from_youtubedl(video_link):
    print(" ➤ [ X ] Attempting to download tweet info via YoutubeDL: " + video_link)
    with youtube_dl.YoutubeDL({'outtmpl': '%(id)s.%(ext)s'}) as ydl:
        result = ydl.extract_info(video_link, download=False)
        vnf = video_info(result['url'], video_link, result['description'].rsplit(' ',1)[0], result['thumbnail'], result['uploader'])
        return vnf

def link_to_vnf(video_link): # Return a VideoInfo object or die trying
    if config['config']['method'] == 'hybrid':
        try:
            return link_to_vnf_from_api(video_link)
        except Exception as e:
            print(" ➤ [ !!! ] API Failed")
            print(e)
            return link_to_vnf_from_youtubedl(video_link)
    elif config['config']['method'] == 'api':
        try:
            return link_to_vnf_from_api(video_link)
        except Exception as e:
            print(" ➤ [ X ] API Failed")
            print(e)
            return None
    elif config['config']['method'] == 'youtube-dl':
        try:
            return link_to_vnf_from_youtubedl(video_link)
        except Exception as e:
            print(" ➤ [ X ] Youtube-DL Failed")
            print(e)
            return None
    else:
        print("Please set the method key in your config file to 'api' 'youtube-dl' or 'hybrid'")
        return None

def get_vnf_from_link_cache(video_link):
    """
    TODO: Use Elasticache to store the VNFs
    """
    return None

def add_vnf_to_link_cache(video_link, vnf):
    """
    TODO: Use Elasticache to store the VNFs
    """
    link_cache[video_link] = vnf

def embed(video_link, vnf):
    print(" ➤ [ E ] Embedding " + vnf['url'])
    if vnf['thumbnail'] == "Non video link with url":
        print(" ➤ [ NV ] Redirecting Non Video Tweet to Twitter")
        return redirect(vnf['url'], 301)

    if vnf['url'].startswith('https://t.co') is not True:
        desc = re.sub(r' http.*t\.co\S+', '', vnf['description'])
        urlUser = urllib.parse.quote(vnf['uploader'])
        urlDesc = urllib.parse.quote(desc)
        urlLink = urllib.parse.quote(video_link)
        return render_template(
            'template.html',
            vidlink=vnf['url'],
            vidurl=vnf['url'],
            desc=desc,
            pic=vnf['thumbnail'],
            user=vnf['uploader'],
            video_link=video_link,
            color=config['config']['color'],
            appname=config['config']['appname'],
            repo=config['config']['repo'],
            url=config['config']['url'],
            urlDesc=urlDesc,
            urlUser=urlUser,
            urlLink=urlLink
        )
    else:
        return redirect(vnf['url'], 301)

def o_embed_gen(description, user, video_link):
    out = {
        "type":"video",
        "version":"1.0",
        "provider_name":"TwitFix",
        "provider_url":"https://github.com/robinuniverse/twitfix",
        "title":description,
        "author_name":user,
        "author_url":video_link
    }

    return out
