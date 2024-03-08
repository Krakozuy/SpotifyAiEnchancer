import spotipy
import json
import anthropic
import spotipy
import json
import anthropic
import logging
import sqlite3
import schedule
import time
import datetime
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask, redirect, request, redirect, url_for, render_template, session
from flask_session import Session
from apscheduler.schedulers.background import BackgroundScheduler
from spotipy.oauth2 import SpotifyOAuth

# Set your Spotify app credentials
SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5003/callback'
CLUDE_API_KEY = ''

# Set the scope to 'user-library-read' to access liked songs
scope = "user-library-read user-library-modify user-top-read playlist-modify-public"

# Authenticate with Spotify
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=scope)

sp = None
# Auth in Claude
ai = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=CLUDE_API_KEY,
)

scheduler = BackgroundScheduler()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your-secret-key'  # replace with your secret key
Session(app)


@app.errorhandler(500)
def internal_error(exception):
    return render_template("error500.html")


def fetch_liked_tracks(sp, limit):
    liked_tracks = []
    for i in range(0, limit, 50):
        results = sp.current_user_saved_tracks(limit=min(50, limit - i), offset=i)
        liked_tracks.extend(results['items'])

    # Convert the list of tracks to a string
    tracklist = ""
    for track in liked_tracks:
        track_name = track['track']['name']
        artist_name = track['track']['artists'][0]['name']
        tracklist += f"{artist_name} - {track_name}\n"
    print(tracklist)
    return tracklist


def clear_playlist(sp, playlist_id):
    sp.playlist_replace_items(playlist_id, [])


def create_playlist_if_not_exists(sp, user_id, playlist_name):
    playlists = sp.user_playlists(user_id)
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            return playlist['id']

    playlist = sp.user_playlist_create(user_id, playlist_name)
    return playlist['id']


def add_tracks_to_playlist(sp, playlist_id, recomendation):
    # Parse the JSON string into a Python dictionary
    tracks_dict = json.loads(recomendation)

    # Clear the playlist
    clear_playlist(sp, playlist_id)

    track_ids = []
    for track in tracks_dict['tracks']:
        logging.info(f"Trying to add track: {track['artist']} - {track['song']}")
        results = sp.search(q='artist:' + track['artist'] + ' track:' + track['song'], type='track')
        added = False
        for item in results['tracks']['items']:
            if item['name'].lower() == track['song'].lower() and item['artists'][0]['name'].lower() == track['artist'].lower():
                track_ids.append(item['id'])
                added = True
                break
        if added:
            logging.info(f"Added track: {track['artist']} - {track['song']}")
        else:
            logging.info(f"Could not add track: {track['artist']} - {track['song']}")

    if track_ids:
        sp.playlist_add_items(playlist_id, track_ids)


# Get recomendations
def get_ai_recomendations(liked_tracks, mood):
    logging.info("Start AI")
    response = ai.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        temperature=1,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Assume you are a personal music expert with vast industry knowledge. You are the most well-known music critic in the world. I will send you a list of my favorite songs and the commands for what to do with them"
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Understood. As a renowned music expert and critic, I'm ready to analyze and provide insights on your favorite songs based on your commands. Please send me your list of songs and let me know what you'd like me to do with them. I'll use my extensive industry knowledge to provide you with the most valuable and relevant information."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Here is my top songs:\n" + liked_tracks
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "That's an impressive and diverse list of songs! Here are a few things I can do with your favorite tracks:\n\n1. Analyze the most common genres and subgenres represented to identify your core musical tastes. \n\n2. Look for patterns in the artists, time periods, languages, and countries to provide insights into your preferences.\n\n3. Identify lesser-known or up-and-coming artists on the list that you seem to favor.\n\n4. Suggest other songs and artists you may enjoy based on your favorites, helping you discover new music.\n\n5. Create playlists grouped by genre, mood, energy level, decade or other factors to organize your library.\n\n6. Provide a writeup discussing themes, musical styles, lyrics and what these songs say about you as a listener.\n\n7. Highlight songs that have been critically acclaimed or culturally significant to give context to your tastes.\n\n8. Compare your favorites to general popularity to see how your tastes align with or differ from mainstream preferences.\n\n9. Identify potential songs or artists missing from your list that you would be likely to enjoy.\n\n10. Discuss the overall breadth and eclecticism of your musical palate based on the variety represented.\n\nLet me know which of these analyses or tasks would be most interesting and useful for you! I'm happy to dive deep into your excellent song list."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe what music taste I have."
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Based on the extensive list of songs you provided, you have a highly eclectic and diverse music taste that spans many genres, decades, and languages. Your favorites showcase a strong appreciation for alternative, electronic, hip-hop, rock, and world music styles.\n\nIn the alternative and rock realms, you seem to favor energetic, rebellious, and emotionally charged songs from artists like Muse, The Killers, Refused, and grandson. Classic rock acts like Led Zeppelin and Aerosmith also appear, showing an appreciation for the genre's roots.\n\nYour electronic tastes are similarly varied, ranging from the experimental works of Gesaffelstein and The Glitch Mob to the more dance-oriented sounds of Flux Pavilion and The Chemical Brothers. Acts like Kaleida and Moskva-Kassiopeya showcase a fondness for atmospheric, cinematic electronic music as well.\n\nHip-hop is another core component of your musical palate, with a mix of classic artists like 2Pac and Eminem alongside modern stars like Kendrick Lamar, A$AP Rocky, and Big Baby Tape. You seem drawn to rappers known for their lyrical prowess and storytelling abilities.\n\nInterestingly, your list also shows a strong affinity for music in languages other than English, particularly Russian. Artists like Хаски, Shortparis, and Oligarkh demonstrate a deep connection to Russian language hip-hop, rock, and electronic scenes.\n\nAcross your favorites, a sense of intensity, authenticity, and boundary-pushing shines through. You appear to value artists who take creative risks, blend genres in innovative ways, and express raw, honest emotions. At the same time, the presence of acts like Rosemary Clooney and Enrique Iglesias suggests an openness to more classic pop sounds as well.\n\nOverall, your music taste is defined by its breadth, depth, and willingness to explore sounds from all corners of the musical spectrum. You have a keen ear for quality and originality that transcends language and genre boundaries."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Your goal will be to recommend the top 25 songs that I will like and that are NOT on this list. Focus on the less famous and niche songs/bands. I also feel " + mood + " today.  Give me you answer as json whith tracks. Only json in response, no additional text and commentary.\nYou shoud return JSON strictly in defined format.\nDefied format:\n{\n\"tracks\": [\n{\n\"artist\": \"Artist 1\",\n\"song\": \"Song 1\"\n},\n{\n\"artist\": \"Artist 2\",\n\"song\": \"Song 2\"\n} \n]\n}"
                    }
                ]
            }
        ]
    )
    json_data = json.loads(response.model_dump_json())
    output = json_data['content'][0]['text']
    logging.info("AI Response: " + output)
    return output


def check_message(liked_tracks, mood):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Assume you are a personal music expert with vast industry knowledge. You are the most well-known music critic in the world. I will send you a list of my favorite songs and the commands for what to do with them"
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Understood. As a renowned music expert and critic, I'm ready to analyze and provide insights on your favorite songs based on your commands. Please send me your list of songs and let me know what you'd like me to do with them. I'll use my extensive industry knowledge to provide you with the most valuable and relevant information."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Here is my top songs:\n" + liked_tracks
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "That's an impressive and diverse list of songs! Here are a few things I can do with your favorite tracks:\n\n1. Analyze the most common genres and subgenres represented to identify your core musical tastes. \n\n2. Look for patterns in the artists, time periods, languages, and countries to provide insights into your preferences.\n\n3. Identify lesser-known or up-and-coming artists on the list that you seem to favor.\n\n4. Suggest other songs and artists you may enjoy based on your favorites, helping you discover new music.\n\n5. Create playlists grouped by genre, mood, energy level, decade or other factors to organize your library.\n\n6. Provide a writeup discussing themes, musical styles, lyrics and what these songs say about you as a listener.\n\n7. Highlight songs that have been critically acclaimed or culturally significant to give context to your tastes.\n\n8. Compare your favorites to general popularity to see how your tastes align with or differ from mainstream preferences.\n\n9. Identify potential songs or artists missing from your list that you would be likely to enjoy.\n\n10. Discuss the overall breadth and eclecticism of your musical palate based on the variety represented.\n\nLet me know which of these analyses or tasks would be most interesting and useful for you! I'm happy to dive deep into your excellent song list."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe what music taste I have."
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Based on the extensive list of songs you provided, you have a highly eclectic and diverse music taste that spans many genres, decades, and languages. Your favorites showcase a strong appreciation for alternative, electronic, hip-hop, rock, and world music styles.\n\nIn the alternative and rock realms, you seem to favor energetic, rebellious, and emotionally charged songs from artists like Muse, The Killers, Refused, and grandson. Classic rock acts like Led Zeppelin and Aerosmith also appear, showing an appreciation for the genre's roots.\n\nYour electronic tastes are similarly varied, ranging from the experimental works of Gesaffelstein and The Glitch Mob to the more dance-oriented sounds of Flux Pavilion and The Chemical Brothers. Acts like Kaleida and Moskva-Kassiopeya showcase a fondness for atmospheric, cinematic electronic music as well.\n\nHip-hop is another core component of your musical palate, with a mix of classic artists like 2Pac and Eminem alongside modern stars like Kendrick Lamar, A$AP Rocky, and Big Baby Tape. You seem drawn to rappers known for their lyrical prowess and storytelling abilities.\n\nInterestingly, your list also shows a strong affinity for music in languages other than English, particularly Russian. Artists like Хаски, Shortparis, and Oligarkh demonstrate a deep connection to Russian language hip-hop, rock, and electronic scenes.\n\nAcross your favorites, a sense of intensity, authenticity, and boundary-pushing shines through. You appear to value artists who take creative risks, blend genres in innovative ways, and express raw, honest emotions. At the same time, the presence of acts like Rosemary Clooney and Enrique Iglesias suggests an openness to more classic pop sounds as well.\n\nOverall, your music taste is defined by its breadth, depth, and willingness to explore sounds from all corners of the musical spectrum. You have a keen ear for quality and originality that transcends language and genre boundaries."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Your goal will be to recommend the top 10 songs that I will like and that are NOT on this list. Focus on the less famous and niche songs/bands. I also feel " + mood + " today.  Give me you answer as json whith tracks. Only json in response, no additional text and commentary.\nYou shoud return JSON strictly in defined format.\nDefied format:\n{\n\"tracks\": [\n{\n\"artist\": \"Artist 1\",\n\"song\": \"Song 1\"\n},\n{\n\"artist\": \"Artist 2\",\n\"song\": \"Song 2\"\n} \n]\n}"
                }
            ]
        }
    ]
    print(messages)


def do_job(user_id, user_token):
    sp = spotipy.Spotify(auth=user_token)
    # Fetch the first 100 liked songs
    tracks = fetch_liked_tracks(sp, 100)
    logging.info("Tracks: " + tracks)
    # get recommendationss
    recomendation_happy = get_ai_recomendations(tracks, "happy")
    recomendation_calm = get_ai_recomendations(tracks, "calm")
    recomendation_energetic = get_ai_recomendations(tracks, "energetic")
    recomendation_working = get_ai_recomendations(tracks, "working")
    logging.info("Recomendation happy: " + recomendation_happy)
    logging.info("Recomendation calm: " + recomendation_calm)
    logging.info("Recomendation energetic: " + recomendation_energetic)
    logging.info("Recomendation working: " + recomendation_working)
    # Create the "AI Recommendation" playlist if it doesn't exist
    playlist_id_happy = create_playlist_if_not_exists(sp, user_id, "Happy")
    playlist_id_calm = create_playlist_if_not_exists(sp, user_id, "Calm")
    playlist_id_energetic = create_playlist_if_not_exists(sp, user_id, "Energetic")
    playlist_id_working = create_playlist_if_not_exists(sp, user_id, "Working")
    # Add tracks to the playlist from a JSON file
    add_tracks_to_playlist(sp, playlist_id_happy, recomendation_happy)  # Add the tracks to the playlist
    logging.info("Added to playlist 1")
    add_tracks_to_playlist(sp, playlist_id_calm, recomendation_calm)  # Add the tracks to the playlist
    logging.info("Added to playlist 2")
    add_tracks_to_playlist(sp, playlist_id_energetic, recomendation_energetic)  # Add the tracks to the playlist
    logging.info("Added to playlist 3")
    add_tracks_to_playlist(sp, playlist_id_working, recomendation_working)  # Add the tracks to the playlist
    logging.info("Added to playlist 4")
    conn = sqlite3.connect('spotify_users.db')  # Connect to the database
    cursor = conn.cursor()  # Create a cursor object
    now = datetime.now()  # Get the current date and time
    cursor.execute("UPDATE users SET last_update_time=? WHERE user_id=?", (now, user_id))
    conn.commit()  # Commit the changes
    conn.close()  # Close the connection
    pass


def do_simple_job():
    music_list = fetch_liked_tracks(sp, 100)
    return music_list


def write_to_db(user_id, user_token):
    conn = sqlite3.connect('spotify_users.db')  # Connect to the database
    cursor = conn.cursor()  # Create a cursor object

    # Check if user_id already exists in the database
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    # If user_id does not exist, insert a new record
    if data is None:
        cursor.execute("INSERT INTO users (user_id, user_token) VALUES (?, ?)", (user_id, user_token))
    # If user_id exists, update the last_update_time
    else:
        cursor.execute("UPDATE users SET user_token=? WHERE user_id=?", (user_token, user_id))

    conn.commit()  # Commit the changes
    conn.close()  # Close the connection


def check_updates_job():
    conn = sqlite3.connect('spotify_users.db')  # Connect to the database
    cursor = conn.cursor()  # Create a cursor object

    hours_ago = datetime.now() - timedelta(hours=10)

    # Select users where last_update_time is more than 2 days old
    cursor.execute("SELECT * FROM users WHERE last_update_time<? OR last_update_time IS NULL", (hours_ago,))
    data = cursor.fetchall()

    if data:
        for row in data:
            user_id = row[0]  # Assuming user_id is the first column
            user_token = row[2]  # Assuming user_token is the second column
            do_job(user_id, user_token)
    conn.close()  # Close the connection


def check_updates_job_simple():
    conn = sqlite3.connect('spotify_users.db')  # Connect to the database
    cursor = conn.cursor()  # Create a cursor object
    hours_ago = datetime.now() - timedelta(hours=10)
    # Select users where last_update_time is more than 2 days old
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()
    if data:
        for row in data:
            user_id_db = row[0]  # Assuming user_id is the first column
            user_token_db = row[2]  # Assuming user_token is the second column
            print("DB user: " + user_id_db)
            print("DB token: " + user_token_db)
    conn.close()  # Close the connection

@app.route('/')
def index():
    return render_template('main.html')


@app.route('/login')
def login():
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                            client_secret=SPOTIPY_CLIENT_SECRET,
                            redirect_uri=SPOTIPY_REDIRECT_URI,
                            scope=scope)  # force users to always login
    auth_url = sp_oauth.get_authorize_url()
    print("Auth url:" + auth_url)
    return redirect(auth_url)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    print("Code: " + code)
    token_info = sp_oauth.get_access_token(code, check_cache=False)
    session['token'] = token_info['access_token']
    print("User id session: " + session['token'])
    print("User id sp: " + token_info['access_token'])
    return redirect(url_for('done'))

@app.route('/done')
def done():
    sp = spotipy.Spotify(auth=session['token'])
    session['user_id'] = sp.current_user()['id']
    print("User id session: " + session['user_id'])
    print("User id sp: " + sp.current_user()['id'])
    write_to_db(session['user_id'], session['token'])
    do_job(session['user_id'], session['token'])
    return render_template('done.html')


schedule.every().day.at("10:00").do(check_updates_job)

if __name__ == "__main__":
    app.run(debug=True, port=5003)
    while True:
        schedule.run_pending()
        time.sleep(1)
