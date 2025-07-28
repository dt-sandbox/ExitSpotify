import os
import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- Spotify Authentication via Secrets ---
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id,
    client_secret=client_secret))

# --- Function: extract playlist data ---
def get_playlist_data(playlist_url):
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    playlist_info = sp.playlist(playlist_id)
    playlist_name = playlist_info['name']

    results = sp.playlist_items(playlist_id, additional_types=['track'])

    tracks = []
    while results:
        for item in results['items']:
            track = item['track']
            if track:
                tracks.append({
                    'Artist': ', '.join([a['name'] for a in track['artists']]),
                    'Title': track['name'],
                    'Album': track['album']['name'],
                    'Duration': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] // 1000) % 60:02}",
                    'ISRC': track['external_ids'].get('isrc', 'N/A')
                })
        results = sp.next(results) if results['next'] else None

    df = pd.DataFrame(tracks)
    return playlist_name, df

# --- Streamlit Page Settings ---
st.set_page_config(page_title="ExitSpotify", page_icon="🛑", layout="centered")

# --- Intro ---
st.title("🛑 ExitSpotify")

st.markdown("""
*Daniel Ek invests more in weapons than he pays many artists. That’s disgusting — but Spotify itself is even worse.*  
Music has become a service, a commodity. Everyone talks about culture, but no one really does much.  
**Boycotting Spotify is a concrete step toward giving music value again.**  
I hope this tool helps you migrate elsewhere.  
**Remember: if it’s easy, it’s not a protest — it’s virtue signaling.**
""")

# --- Input field ---
playlist_url = st.text_input("🎧 Paste the Spotify playlist link")

if st.button("🎛️ Generate"):
    if playlist_url:
        try:
            playlist_name, df = get_playlist_data(playlist_url)

            st.subheader(f"📓 {playlist_name}")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name='playlist.csv', mime='text/csv')

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please paste a playlist link.")

# --- Footer / Disclaimer ---
st.divider()
st.markdown("""
*This tool uses the [Spotify Web API](https://developer.spotify.com/documentation/web-api/) to retrieve publicly available data.  
It is not affiliated, endorsed, or certified by Spotify AB. All names, logos, and trademarks are the property of their respective owners.*
""")
