from modules.events.random_timed_event import RandomTimedEvent
import threading

class RandomVSCEvent(RandomTimedEvent):
    """
    A class to represent a random Virtual Safety Car (VSC) event in the iRacing simulator.

    Attributes:
        restart_proximity (int): Proximity threshold for restarting the race.
        max_vsc_duration (int): Maximum duration for the VSC.
        max_laps_behind_leader (int): Maximum laps a car can be behind the leader.
        wave_arounds (bool): Flag to indicate if wave arounds are allowed.
        notify_on_skipped_caution (bool): Flag to indicate if notifications should be sent when a caution is skipped.
        reason (str): The reason for the VSC.
    """

    def __init__(self, restart_proximity=None, max_vsc_duration=None, wave_arounds=False, notify_on_skipped_caution=False, *args, **kwargs):
        """
        Initializes the RandomVSC class.

        Args:
            restart_proximity (int, optional): Proximity threshold for restarting the race. Defaults to None.
            max_vsc_duration (int, optional): Maximum duration for the VSC. Defaults to None.
            max_laps_behind_leader (int, optional): Maximum laps a car can be behind the leader. Defaults to 3.
            wave_arounds (bool, optional): Flag to indicate if wave arounds are allowed. Defaults to False.
            notify_on_skipped_caution (bool, optional): Flag to indicate if notifications should be sent when a caution is skipped. Defaults to False.
        """
        self.restart_proximity = int(restart_proximity)
        self.max_vsc_duration = int(max_vsc_duration)
        self.wave_arounds = wave_arounds
        self.notify_on_skipped_caution = notify_on_skipped_caution
        self.restart_ready = threading.Event()
        self.double_file = False
        super().__init__(*args, **kwargs)
        self.reason = self.generate_random_caution_reason()

    def event_sequence(self):
        """
        Executes the event sequence for a random VSC.
        """
        if self.is_caution_active() or self.busy_event.is_set():
            if self.notify_on_skipped_caution:
                self._chat('Additional caution skipped due to active caution.')
            return

        self.busy_event.set()
        self.restart_ready.clear()
        self._chat(self.reason)
        self._chat('VSC will begin at the Start/Finish Line')

        last_step = self.get_current_running_order()
        session_time = self.sdk['SessionTimeRemain']

        # wait for someone to start the next lap
        lead_lap = max([car['LapCompleted'] for car in last_step])
        while not any([car['LapCompleted'] > lead_lap for car in self.get_current_running_order()]):
            last_step = self.get_current_running_order()
            self.sleep(1)
        restart_order = []

        self._chat('Double Yellow Flags in Sector 1')
        self._chat('No Overtaking in Sector 1')

        wrongmap = {}

        while not self.ready_to_restart():
            this_step = self.get_current_running_order()
            for car in this_step:
                if car['CarNumber'] not in [c['CarNumber'] for c in restart_order]:
                    if self.car_has_completed_lap(car, last_step, this_step) and not self.sdk['CarIdxOnPitRoad'][car['CarIdx']]:
                        restart_order.append(car)
                        self.logger.debug(f'Added {car["CarNumber"]} to restart order (completed lap).')
                    if self.car_has_left_pits(car, last_step, this_step):
                        restart_order.append(car)
                        self.logger.debug(f'Added {car["CarNumber"]} to restart order (left pits).')
                    if car['CarNumber'] in [c['CarNumber'] for c in restart_order]:
                        # if we've just added them to the restart order, check if they're a lap down
                        if car['total_completed']<max([l['total_completed']-1 for l in restart_order]):
                            self.logger.debug(f'{car["CarNumber"]} is a lap down.')
                            self._chat(f'/{car["CarNumber"]} you may now safely pass the field to unlap yourself.')
                        # make sure all the lap down cars are at the end of the restart order, but otherwise keep the order the same
                        restart_order = sorted(restart_order, key=lambda x: int(2 if x['total_completed']>max([l['total_completed']-1 for l in restart_order]) else 1) - (restart_order.index(x) * 0.01), reverse=True)
                        self.logger.debug(f'Restart order: {[car["CarNumber"] for car in restart_order]}')


            last_step = this_step
            correct_order = [car['CarNumber'] for car in restart_order]

            running_order_uncorrected = self.get_current_running_order()
            running_order_lap_down_corrected = sorted(running_order_uncorrected, key=lambda x: int(2 if x['total_completed']>max([l['total_completed']-1 for l in running_order_uncorrected]) else 1) + x['total_completed']/1000, reverse=True)
            actual_order = [car['CarNumber'] for car in running_order_lap_down_corrected if car['CarNumber'] in correct_order]


            for car in actual_order:
                cars_that_should_be_ahead = correct_order[:correct_order.index(car)]
                cars_that_are_behind = actual_order[actual_order.index(car) + 1:]
                cars_incorrectly_behind = [car for car in cars_that_are_behind if car in cars_that_should_be_ahead]
                wrongmap[car] = cars_incorrectly_behind

            if session_time - self.sdk['SessionTimeRemain'] > 10:
                for car, cars_incorrectly_behind in wrongmap.items():
                    if cars_incorrectly_behind:
                        session_time = self.sdk['SessionTimeRemain']
                        self.logger.warning(f'Car {car} ahead of cars {cars_incorrectly_behind} when they should be behind.')
                        self._chat(f'/{car} let {", ".join(cars_incorrectly_behind)} by.')

            self.sleep(1)

        if self.double_file:
            self.restart_ready.clear()
            self._chat('Double File Restart')
            left_line = []
            right_line = []
            for i, car in enumerate(restart_order):
                if i % 2 == 0:
                    right_line.append(car)
                    message = f'/{car["CarNumber"]} line up on the right '
                    if len(right_line) > 1:
                        message += f'behind car {right_line[-2]["CarNumber"]}'
                    self._chat(message)
                else:
                    left_line.append(car)
                    message = f'/{car["CarNumber"]} line up on the left '
                    if len(left_line) > 1:
                        message += f'behind car {left_line[-2]["CarNumber"]}'
                    self._chat(message)
            left_wrongmap = {}
            right_wrongmap = {}
            while not self.ready_to_restart():
                running_order_uncorrected = self.get_current_running_order()
                running_order_lap_down_corrected = sorted(running_order_uncorrected, key=lambda x: int(2 if x['total_completed']>max([l['total_completed']-1 for l in running_order_uncorrected]) else 1) + x['total_completed']/1000, reverse=True)
                actual_order = [car['CarNumber'] for car in running_order_lap_down_corrected if car['CarNumber'] in correct_order]
                for car in left_line:
                    cars_that_should_be_ahead = [c['CarNumber'] for c in left_line[:left_line.index(car)]]
                    cars_that_are_behind = actual_order[actual_order.index(car['CarNumber']) + 1:]
                    cars_incorrectly_behind = [car for car in cars_that_are_behind if car in cars_that_should_be_ahead]
                    left_wrongmap[car['CarNumber']] = cars_incorrectly_behind
                for car in right_line:
                    cars_that_should_be_ahead = [c['CarNumber'] for c in right_line[:right_line.index(car)]]
                    cars_that_are_behind = actual_order[actual_order.index(car['CarNumber']) + 1:]
                    cars_incorrectly_behind = [car for car in cars_that_are_behind if car in cars_that_should_be_ahead]
                    right_wrongmap[car['CarNumber']] = cars_incorrectly_behind
                self.sleep(1)
                if session_time - self.sdk['SessionTimeRemain'] > 10:
                    for car, cars_incorrectly_behind in left_wrongmap.items():
                        if cars_incorrectly_behind:
                            session_time = self.sdk['SessionTimeRemain']
                            self.logger.warning(f'Car {car} ahead of cars {cars_incorrectly_behind} when they should be behind.')
                            self._chat(f'/{car} stay behind {", ".join(cars_incorrectly_behind)} on the left.')
                    for car, cars_incorrectly_behind in right_wrongmap.items():
                        if cars_incorrectly_behind:
                            session_time = self.sdk['SessionTimeRemain']
                            self.logger.warning(f'Car {car} ahead of cars {cars_incorrectly_behind} when they should be behind.')
                            self._chat(f'/{car} stay behind {", ".join(cars_incorrectly_behind)} on the right.')




        self._chat('The field has formed up and the VSC will end soon.')
        for car, cars_incorrectly_behind in wrongmap.items():
            if cars_incorrectly_behind:
                self.logger.error(f'Car {car} restarted ahead of cars {cars_incorrectly_behind}.')

        self.busy_event.clear()

    def ready_to_restart(self):
        """
        Checks if the field is ready to restart.

        Returns:
            bool: True if the field is ready to restart, False otherwise.
        """
        return self.restart_ready.is_set()

