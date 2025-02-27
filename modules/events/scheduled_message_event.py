from modules.events.random_timed_event import TimedEvent

class ScheduledMessageEvent(TimedEvent):
    """
    A class to represent a scheduled message event in the iRacing simulator.
    """

    def __init__(self, message: str, race_control: bool = False, *args, **kwargs):
        """
        Initializes the ScheduledMessageEvent class.

        Args:
            message (str): The message to send.
        """
        super().__init__(*args, **kwargs)
        self.message = message
        self.race_control = race_control

    def event_sequence(self):
        """
        Sends the message.
        """
        self._chat(self.message, race_control=self.race_control)

    @staticmethod
    def ui(ident=''):
        import streamlit as st
        col1, col2, col3 = st.columns([1, 4, 1])
        return {
            'event_time': col1.number_input("Event Time (min)", value=5.0, key=f'{ident}event_time') * 60,
            'message': col2.text_input('Message', key=f'{ident}message', value=''),
            'race_control': col3.checkbox('Send to Race Control', key=f'{ident}race_control', value=False)
        }
