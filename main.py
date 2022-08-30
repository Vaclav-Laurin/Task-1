import os
import pandas
import psutil
from datetime import datetime
from pynput import keyboard


class Process:
    
    def __init__(self):
        self.data_path = ""
        self.interval = 0
        self.is_on = True
        self.processes = []
        self.process_name = ""
        self.process_path = ""
        self.run_time = 0

        self.get_data()

        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    # Gets inputs and validates it (if args are wrong, it asks for inputs again)
    def get_data(self):
        # Just in case somebody will wrap an entire path in double quotes
        self.process_path = input("Type in an absolute path of the process to launch: ").replace('"', '')

        try:
            self.interval = float(input("Type in an interval in seconds: "))
        except ValueError:
            print("Interval should be a number.")

        # Requirements to be met
        conditions = [
            {
                "condition": os.path.exists(self.process_path),
                "message": f"Path '{self.process_path}' does not exists."
            },
            {
                "condition": self.process_path.endswith(".exe"),
                "message": f"'{self.process_path}' is not an executable file."
            },
            {
                "condition": self.interval > 0,
                "message": "Interval should have a value greater, than 0."
            }
        ]

        for condition in conditions:
            if not condition["condition"]:
                print(condition["message"])

                self.get_data()
                break
        else:
            self.process_name = os.path.basename(self.process_path).lower()

            dot_index = self.process_name.find('.')
            date = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            name = self.process_name[:dot_index]
            self.data_path = os.path.join(os.path.dirname(__file__), f"data\{name}_{date}.csv")

            # If the folder does not exist, create it
            if not os.path.exists(os.path.dirname(self.data_path)):
                os.mkdir(os.path.dirname(self.data_path))

            to_save = [[
                self.process_path,
                self.run_time,
                0,
                0,
                0,
                0
            ]]

            if not self.is_running():
                self.save_data(to_save=to_save)

    # Checks if process with the same path is currently running
    def is_running(self):
        for process in psutil.process_iter():
            if process.name().lower() == self.process_name:
                self.process = process

                return True

        return False

    # Function bound to the key listener
    def on_press(self, key):
        if key == keyboard.Key.esc:
            self.is_on = False

    # Launches a process using provided path
    def process_launch(self):
        try:
            os.startfile(self.process_path)
            print(f"The process '{self.process_path}' has been successfully launched")

            # Finds the launched process (or processes if one executable launched several processes)
            # and stores it
            for process in psutil.process_iter():

                if process.name().lower() == self.process_name:
                    self.processes.append(process)
        except PermissionError as e:
            print(str(e).title())

    # Handles an entire program logic (launches current Python script)
    def processor(self):

        if self.is_running():
            print(
                f"The process '{self.process.name()}' (PID: {self.process.pid}) has already been launched.",
                "Close the process and try again."
            )
        else:
            self.process_launch()

            # Check if process was found
            if self.processes:
                while self.is_on:
                    cpu_percentage = 0
                    working_set = 0
                    private_bytes = 0
                    open_handles_num = 0

                    # Check if the process is still alive
                    try:
                        # Iterate through all processes with the same name and summarize the data
                        for process in self.processes:
                            cpu_percentage += process.cpu_percent(interval=self.interval)
                            memory_usage = process.memory_full_info()
                            working_set += memory_usage.wset
                            private_bytes += memory_usage.uss
                            open_handles_num += len(process.open_files())

                        self.run_time += self.interval

                        to_save = [[
                            self.process_path,
                            self.run_time,
                            cpu_percentage,
                            working_set,
                            private_bytes,
                            open_handles_num
                        ]]
                        self.save_data(to_save=to_save)
                    except psutil.NoSuchProcess as e:
                        print(str(e).title())

                        respond = input("Do You want to continue? (YES/NO)").upper()

                        # Restarts the program
                        if respond == 'YES':
                            self.get_data()
                            self.processor()
                        else:
                            self.is_on = False

                # Kills the process after the end of data collecting
                if self.is_running():
                    for process in self.processes:
                        process.kill()

    def save_data(self, to_save):
        column_names = [
            "Process Path",
            "Run Time, s",
            "CPU Usage, %",
            "Memory Consumption: Working Set, Bytes",
            "Memory Consumption: Private Bytes, Bytes",
            "Number of Open Handles"
        ]
        new_data = pandas.DataFrame(to_save, columns=column_names).set_index(column_names[0])

        # Try read the file. If it does not exist, create it
        try:
            data = pandas.read_csv(self.data_path).set_index(column_names[0])
        except FileNotFoundError:
            new_data.to_csv(self.data_path)
        else:
            result = pandas.concat([data, new_data], axis=0)
            result.to_csv(self.data_path)


print("Welcome back!", "Provide some data below or press Esc to quit and save the data")

try:
    process = Process()
    process.processor()
except PermissionError as e:
    print(str(e).title())