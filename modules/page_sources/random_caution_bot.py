import random
import streamlit as st
import uuid
from modules.events.random_caution_event import RandomCautionEvent
from modules.subprocess_manager import SubprocessManager
import logging
from streamlit_autorefresh import st_autorefresh

logger = st.session_state.logger


def empty_caution():
    """
    Creates an empty caution dictionary with default values.

    Returns:
        dict: A dictionary representing an empty caution with a unique ID, default likelihood, and no instance.
    """
    return {'id': uuid.uuid4(), 'likelihood': 75, 'instance': None}

def start_sequence():
    """
    Starts the caution sequence by initializing RandomCaution instances based on the session state settings.
    """
    cautions = [
        RandomCautionEvent(
            pit_close_advance_warning=st.session_state.pit_close_advance_warning,
            pit_close_max_duration=st.session_state.pit_close_maximum_duration,
            max_laps_behind_leader=st.session_state.max_laps_behind_leader,
            wave_arounds=st.session_state.wave_arounds,
            min_time=int(st.session_state.caution_window_start) * 60,
            max_time=int(st.session_state.caution_window_end) * 60,
            notify_on_skipped_caution=st.session_state.notify_skipped
        )
        for caution in st.session_state.cautions
        if random.randrange(0, 100) <= int(caution['likelihood'])
    ]

    st.session_state.caution_runner = cautions
    st.session_state.spm = SubprocessManager([c.run for c in cautions])
    st.session_state.spm.start()
    st.session_state.refresh = True

def stop_sequence():
    """
    Stops the caution sequence and refreshes the Streamlit page.
    """
    if 'spm' in st.session_state:
        st.session_state.spm.stop()
    st.session_state.refresh = False
    st_autorefresh(limit=1)

def ui():
    """
    Renders the Streamlit UI for configuring and managing random cautions.
    """
    if 'refresh' not in st.session_state:
        st.session_state.refresh = False
    if 'cautions' not in st.session_state:
        st.session_state.cautions = [empty_caution(), empty_caution()]

    st.header("Global Settings")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    st.session_state.caution_window_start = col1.text_input("Window Start (min)", "5")
    st.session_state.caution_window_end = col2.text_input("Window End (min)", "-15")
    st.session_state.pit_close_advance_warning = col3.text_input("Pit Close Warning (sec)", "5")
    st.session_state.pit_close_maximum_duration = col4.text_input("Max Pit Close Time (sec)", "120")
    st.session_state.max_laps_behind_leader = col5.text_input("Max Laps Behind Leader", "3")
    st.session_state.wave_arounds = col6.checkbox("Wave Arounds", value=True)
    st.session_state.notify_skipped = col7.checkbox("Notify on Skipped Caution")
    st.write('---')

    for i, caution in enumerate(st.session_state.cautions):
        col1, col2, col3, _ = st.columns((1, 1, 1, 2))
        col1.subheader(f"Caution {i + 1}")
        st.session_state.cautions[i]['likelihood'] = col2.text_input("Likelihood (%)", caution['likelihood'], key=f"likelihood_{caution['id']}")
        col3.button("Remove", on_click=lambda: st.session_state.cautions.pop(i), key=f"remove_{caution['id']}")

    st.write('---')
    st.button("Add Caution", on_click=lambda: st.session_state.cautions.append(empty_caution()))

    col1, col2 = st.columns(2)
    col1.button("Start", on_click=start_sequence)
    col2.button("Cancel", on_click=stop_sequence)

    if st.session_state.refresh:
        st_autorefresh()
    if 'spm' in st.session_state and not any(c.is_alive() for c in st.session_state.spm.threads):
        st.session_state.refresh = False
        st_autorefresh(limit=1)

random_caution_bot = st.Page(ui, title='Random Caution Bot', url_path='random_caution_bot', icon='🚔')