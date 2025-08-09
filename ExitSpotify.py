import os
import re
from urllib.parse import urlparse

import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# ---------------------- Auth ----------------------
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret))

# ---------------------- Helpers (UI-only) ----------------------
def _extract_playlist_id(s: str) -> str:
    s = s.strip()
    if re.fullmatch(r"[A-Za-z0-9]{22}", s):
        return s
    if s.startswith("spotify:playlist:"):
        return s.split(":")[-1]
    p = urlparse(s)
    seg = p.path.strip("/").split("/")[-1]
    return seg.split("?")[0]

def _parse_mmss_to_ms(x: str) -> int:
    # "m:ss" -> ms
    try:
        m, s = x.split(":")
        return (int(m) * 60 + int(s)) * 1000
    except Exception:
        return 0

def _format_ms(ms: int) -> str:
    s = ms // 1000
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:d}:{m:02d}:{s:02d}"

# ---------------------- Your original data function (unchanged) ----------------------
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

# ---------------------- Page config & light CSS ----------------------
st.set_page_config(page_title="ExitSpotify", page_icon="🛑", layout="wide", menu_items={
    "Get Help": "https://developer.spotify.com/documentation/web-api/",
    "Report a bug": "mailto:you@example.com",
})

st.markdown("""
<style>
/* hero title spacing */
.block-container { padding-top: 2rem; }
/* card look */
.card {
  border: 1px solid rgba(250,250,250,.08);
  border-radius: 16px;
  padding: 1rem;
}
.metric-box {
  border: 1px solid rgba(250,250,250,.08);
  border-radius: 12px;
  padding: .75rem .9rem;
}
.badge {
  display:inline-block; padding:.25rem .6rem; border-radius:999px;
  border:1px solid rgba(250,250,250,.15); margin-right:.4rem; margin-bottom:.3rem;
  font-size:.85rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- Header / Hero ----------------------
c1, c2 = st.columns([1, 2.2])
with c1:
    st.title("🛑 ExitSpotify")
with c2:
    st.write("**Migra le tue playlist in un attimo.** Visualizza la tracklist, filtrala e scarica un CSV pulito.")
    with st.expander("Perché questo strumento?"):
        st.markdown("""
        *Daniel Ek investe più in armi che negli artisti. La musica è diventata commodity.*
        **Boicottare Spotify** è un gesto politico e pratico: dai valore a ciò che ascolti.
        """)

st.divider()

# ---------------------- Sidebar ----------------------
with st.sidebar:
    st.subheader("Come funziona")
    st.markdown("1) Incolla link/URI/ID della **playlist pubblica**\n2) Premi **Generate**\n3) Filtra / esporta CSV")
    st.caption("Accetta: `https://open.spotify.com/playlist/...`, `spotify:playlist:...`, o un ID di 22 caratteri.")
    st.markdown("---")
    st.caption("Credenziali Spotify:")
    st.write("✅ Client ID trovato" if client_id else "❌ Client ID mancante")
    st.write("✅ Client Secret trovato" if client_secret else "❌ Client Secret mancante")
    st.markdown("---")
    if "history" not in st.session_state:
        st.session_state.history = []
    if st.session_state.history:
        st.subheader("Recenti")
        for h in st.session_state.history[-5:][::-1]:
            st.markdown(f"<span class='badge'>📓 {h}</span>", unsafe_allow_html=True)

# ---------------------- Input form ----------------------
with st.form("fetch"):
    st.markdown("### Incolla la playlist")
    playlist_url = st.text_input("🎧 Link / URI / ID", placeholder="https://open.spotify.com/playlist/...")
    col_a, col_b = st.columns([1, 5])
    with col_a:
        submitted = st.form_submit_button("🎛️ Generate", use_container_width=True)
    with col_b:
        st.caption("Suggerimento: puoi incollare anche un ID Spotify (22 caratteri).")

# ---------------------- Main action ----------------------
if submitted:
    if not playlist_url.strip():
        st.warning("Per favore incolla un link/URI/ID di playlist.")
    else:
        try:
            # Dati base (riuso della tua funzione)
            name, df = get_playlist_data(playlist_url)

            # Header card con cover/owner/link (richiede una singola chiamata per info UI)
            try:
                pid = _extract_playlist_id(playlist_url)
                info = sp.playlist(pid, fields="name,images,owner(display_name),external_urls(spotify)")
                cover = (info.get("images") or [{}])[0].get("url", "")
                owner = (info.get("owner") or {}).get("display_name", "Unknown")
                ext = (info.get("external_urls") or {}).get("spotify", "")
            except Exception:
                cover, owner, ext = "", "Unknown", ""

            # calcolo metriche (senza toccare la tua funzione: parse "m:ss")
            df["_ms"] = df["Duration"].map(_parse_mmss_to_ms)
            total_ms = int(df["_ms"].sum())
            avg_ms = int(df["_ms"].mean()) if len(df) else 0

            # ---------------- Header summary ----------------
            st.markdown("### Risultato")
            top_l, top_r = st.columns([1.2, 2])

            with top_l:
                with st.container(border=True):
                    if cover:
                        st.image(cover, use_column_width=True)
                    st.markdown(f"**{name}**")
                    st.caption(f"di **{owner}**")
                    if ext:
                        st.link_button("Apri su Spotify", ext, use_container_width=True)

            with top_r:
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown("**Brani**")
                    st.markdown(f"<div class='metric-box'><h3>{len(df)}</h3></div>", unsafe_allow_html=True)
                with m2:
                    st.markdown("**Durata totale**")
                    st.markdown(f"<div class='metric-box'><h3>{_format_ms(total_ms)}</h3></div>", unsafe_allow_html=True)
                with m3:
                    st.markdown("**Durata media**")
                    st.markdown(f"<div class='metric-box'><h3>{_format_ms(avg_ms)}</h3></div>", unsafe_allow_html=True)

            st.markdown("---")

            # ---------------- Tabs ----------------
            tab_tracks, tab_stats, tab_export = st.tabs(["🎼 Tracks", "📊 Stats", "⬇️ Export"])

            # Tracks tab: filtro veloce + tabella
            with tab_tracks:
                st.caption("Filtra al volo per artista/titolo/album")
                fcol1, fcol2 = st.columns([2, 1])
                with fcol1:
                    q = st.text_input("Filtro testo", placeholder="es. Aphex Twin, ambient, 1996…")
                with fcol2:
                    opt = st.selectbox("Colonna", ["Tutte", "Artist", "Title", "Album"])
                view = df.copy()
                if q:
                    ql = q.lower()
                    if opt == "Tutte":
                        mask = (
                            view["Artist"].str.lower().str.contains(ql, na=False) |
                            view["Title"].str.lower().str.contains(ql, na=False) |
                            view["Album"].str.lower().str.contains(ql, na=False)
                        )
                    else:
                        mask = view[opt].str.lower().str.contains(ql, na=False)
                    view = view[mask]
                st.dataframe(view[["Artist", "Title", "Album", "Duration", "ISRC"]], use_container_width=True, height=480)

            # Stats tab: top artisti
            with tab_stats:
                st.caption("Artisti più frequenti nella playlist")
                top_art = (
                    df.assign(Artist=df["Artist"].str.split(", "))
                      .explode("Artist")
                      .groupby("Artist", as_index=False)
                      .size()
                      .sort_values("size", ascending=False)
                      .head(15)
                )
                if top_art.empty:
                    st.info("Nessuna statistica disponibile.")
                else:
                    st.bar_chart(top_art.set_index("Artist"))

            # Export tab
            with tab_export:
                st.caption("Scarica il CSV pronto all’uso (UTF‑8, separatore virgola)")
                csv = df[["Artist", "Title", "Album", "Duration", "ISRC"]].to_csv(index=False).encode("utf-8")
                safe_name = re.sub(r"[^\w\s.-]", "_", name).strip().replace(" ", "_").lower() or "playlist"
                st.download_button("⬇️ Download CSV", data=csv, file_name=f"{safe_name}.csv", mime="text/csv", use_container_width=True)

            # Cronologia
            if name and (not st.session_state.history or st.session_state.history[-1] != name):
                st.session_state.history.append(name)

            # pulizia colonna tecnica
            df.drop(columns=["_ms"], inplace=True)

        except Exception as e:
            st.error(f"Errore: {e}")

# ---------------------- Footer ----------------------
st.divider()
st.caption("""
Questo tool usa le **Spotify Web API** per dati pubblici. Non affiliato a Spotify AB.
""")

