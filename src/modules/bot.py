"""An interpreter that reads and executes user-created routines."""

import threading
import time
import git
import cv2
import inspect
import importlib
import traceback
from os.path import splitext, basename
from src.common import config, utils
#from src.detection import detection
import numpy as np
import gdi_capture
from rune_solver import find_arrow_directions
from src.routine import components
from src.routine.routine import Routine
from src.routine.components import Point
from src.common.vkeys import click
from src.common.vkeys2 import press
from src.common.interfaces import Configurable


# The rune's buff icon
RUNE_BUFF_TEMPLATE = cv2.imread("assets/rune_buff_template.jpg", 0)
RUNE_BGRA = (255, 102, 221, 255)


class Bot(Configurable):
    """A class that interprets and executes user-defined routines."""

    DEFAULT_CONFIG = {"Interact": "y", "Feed pet": "9"}

    def __init__(self, region=(5, 60, 180, 130)):
        """Loads a user-defined routine on start up and initializes this Bot's main thread."""
        self.hwnd = gdi_capture.find_window_from_executable_name("MapleStory.exe")
        # These values should represent pixel locations on the screen of the mini-map.
        self.top, self.left, self.bottom, self.right = region[0], region[1], region[2], region[3]

        super().__init__("keybindings")
        config.bot = self

        self.rune_active = False
        self.rune_pos = (0, 0)
        self.rune_closest_pos = (0, 0)  # Location of the Point closest to rune
        self.submodules = []
        self.module_name = None
        self.buff = components.Buff()

        self.command_book = {}
        for c in (
            components.Wait,
            components.Walk,
            components.Fall,
            components.Move,
            components.Adjust,
            components.Buff,
        ):
            self.command_book[c.__name__.lower()] = c

        config.routine = Routine()

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        
    def _get_rune_image(self):
        """
        Takes a picture of the application window.
        """
        with gdi_capture.CaptureWindow(self.hwnd) as img:
            if img is None:
                print("MapleStory.exe was not found.")
                return None
            return img.copy()

    def start(self):
        """
        Starts this Bot object's thread.
        :return:    None
        """

        self.update_submodules()
        print("\n[~] Started main bot loop")
        self.thread.start()

    def _main(self):
        """
        The main body of Bot that executes the user's routine.
        :return:    None
        """

        print("\n[~] Initializing detection algorithm:\n")
        print("\n[~] Initialized detection algorithm... or not :P")

        self.ready = True
        config.listener.enabled = True
        last_fed = time.time()
        while True:
            if config.enabled and len(config.routine) > 0:
                # Buff and feed pets
                self.buff.main()
                pet_settings = config.gui.settings.pets
                auto_feed = pet_settings.auto_feed.get()
                num_pets = pet_settings.num_pets.get()
                now = time.time()
                if auto_feed and now - last_fed > 1200 / num_pets:
                    press(self.config["Feed pet"], 1)
                    last_fed = now

                # Highlight the current Point
                config.gui.view.routine.select(config.routine.index)
                config.gui.view.details.display_info(config.routine.index)

                # Execute next Point in the routine
                element = config.routine[config.routine.index]
                if (
                    self.rune_active
                    and isinstance(element, Point)
                    and element.location == self.rune_closest_pos
                ):
                    self._solve_rune()
                element.execute()
                config.routine.step()
            else:
                time.sleep(0.01)

    def _solve_rune(self):
        """
        Moves to the position of the rune and solves the arrow-key puzzle.
        :param model:   The TensorFlow model to classify with.
        :param sct:     The mss instance object with which to take screenshots.
        :return:        None
        """

        move = self.command_book["move"]
        move(*self.rune_pos).execute()
        adjust = self.command_book["adjust"]
        adjust(*self.rune_pos).execute()
        time.sleep(0.2)
        press(
            self.config["Interact"], 1, down_time=0.2
        )  # Inherited from Configurable
        while True:
            print("\nSolving rune:")
            img = self._get_rune_image()
            print("Attempting to solve rune...")
            directions = find_arrow_directions(img)
            if len(directions) == 4:
                print(f"Directions: {directions}.")
                for d, _ in directions:
                    press(d)
                    frame = config.capture.frame
                    rune_buff = utils.multi_match(frame[:frame.shape[0] // 8, :],
                                                  RUNE_BUFF_TEMPLATE,
                                                  threshold=0.9)
                    if rune_buff:
                        rune_buff_pos = min(rune_buff, key=lambda p: p[0])
                        target = (
                            round(rune_buff_pos[0] + config.capture.window["left"]),
                            round(rune_buff_pos[1] + config.capture.window["top"]),
                        )
                        click(target, button="right")
                    rune_location = self._get_rune_location()
                    if rune_location is None:
                        print("Rune has been solved.")
                        self.rune_active = False
                    break
    
    def _get_rune_location(self):
        """
        Returns the (x, y) position of the rune on the mini-map.
        """
        location = self._locate(RUNE_BGRA)
        return location[0] if len(location) > 0 else None

    def _locate(self, *color):
        """
        Returns the median location of BGRA tuple(s).
        """
        with gdi_capture.CaptureWindow(self.hwnd) as img:
            locations = []
            if img is None:
                print("MapleStory.exe was not found.")
            else:
                """
                The screenshot of the application window is returned as a 3-d np.ndarray, 
                containing 4-length np.ndarray(s) representing BGRA values of each pixel.
                """
                # Crop the image to show only the mini-map.
                img_cropped = img[self.left:self.right, self.top:self.bottom]
                height, width = img_cropped.shape[0], img_cropped.shape[1]
                # Reshape the image from 3-d to 2-d by row-major order.
                img_reshaped = np.reshape(img_cropped, ((width * height), 4), order="C")
                for c in color:
                    sum_x, sum_y, count = 0, 0, 0
                    # Find all index(s) of np.ndarray matching a specified BGRA tuple.
                    matches = np.where(np.all((img_reshaped == c), axis=1))[0]
                    for idx in matches:
                        # Calculate the original (x, y) position of each matching index.
                        sum_x += idx % width
                        sum_y += idx // width
                        count += 1
                    if count > 0:
                        x_pos = sum_x / count
                        y_pos = sum_y / count
                        locations.append((x_pos, y_pos))
            return locations
    
    def load_commands(self, file):
        """Prompts the user to select a command module to import. Updates config's command book."""

        utils.print_separator()
        print(f"[~] Loading command book '{basename(file)}':")

        ext = splitext(file)[1]
        if ext != ".py":
            print(f" !  '{ext}' is not a supported file extension.")
            return False

        new_step = components.step
        new_cb = {}
        for c in (components.Wait, components.Walk, components.Fall):
            new_cb[c.__name__.lower()] = c

        # Import the desired command book file
        module_name = splitext(basename(file))[0]
        target = ".".join(["resources", "command_books", module_name])
        try:
            module = importlib.import_module(target)
            module = importlib.reload(module)
        except ImportError:  # Display errors in the target Command Book
            print(" !  Errors during compilation:\n")
            for line in traceback.format_exc().split("\n"):
                line = line.rstrip()
                if line:
                    print(" " * 4 + line)
            print(f"\n !  Command book '{module_name}' was not loaded")
            return

        # Check if the 'step' function has been implemented
        step_found = False
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.lower() == "step":
                step_found = True
                new_step = func

        # Populate the new command book
        for name, command in inspect.getmembers(module, inspect.isclass):
            new_cb[name.lower()] = command

        # Check if required commands have been implemented and overridden
        required_found = True
        for command in [components.Buff]:
            name = command.__name__.lower()
            if name not in new_cb:
                required_found = False
                new_cb[name] = command
                print(f" !  Error: Must implement required command '{name}'.")

        # Look for overridden movement commands
        movement_found = True
        for command in (components.Move, components.Adjust):
            name = command.__name__.lower()
            if name not in new_cb:
                movement_found = False
                new_cb[name] = command

        if not step_found and not movement_found:
            print(
                f" !  Error: Must either implement both 'Move' and 'Adjust' commands, "
                f"or the function 'step'"
            )
        if required_found and (step_found or movement_found):
            self.module_name = module_name
            self.command_book = new_cb
            self.buff = new_cb["buff"]()
            components.step = new_step
            config.gui.menu.file.enable_routine_state()
            config.gui.view.status.set_cb(basename(file))
            config.routine.clear()
            print(f" ~  Successfully loaded command book '{module_name}'")
        else:
            print(f" !  Command book '{module_name}' was not loaded")

    def update_submodules(self, force=False):
        """
        Pulls updates from the submodule repositories. If FORCE is True,
        rebuilds submodules by overwriting all local changes.
        """

        utils.print_separator()
        print("[~] Retrieving latest submodules:")
        self.submodules = []
        repo = git.Repo.init()
        with open(".gitmodules", "r") as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("[") and i < len(lines) - 2:
                    path = lines[i + 1].split("=")[1].strip()
                    url = lines[i + 2].split("=")[1].strip()
                    self.submodules.append(path)
                    try:
                        repo.git.clone(url, path)  # First time loading submodule
                        print(f" -  Initialized submodule '{path}'")
                    except git.exc.GitCommandError:
                        sub_repo = git.Repo(path)
                        if not force:
                            sub_repo.git.stash()  # Save modified content
                        sub_repo.git.fetch("origin", "main")
                        sub_repo.git.reset("--hard", "FETCH_HEAD")
                        if not force:
                            try:  # Restore modified content
                                sub_repo.git.checkout("stash", "--", ".")
                                print(
                                    f" -  Updated submodule '{path}', restored local changes"
                                )
                            except git.exc.GitCommandError:
                                print(f" -  Updated submodule '{path}'")
                        else:
                            print(f" -  Rebuilt submodule '{path}'")
                        sub_repo.git.stash("clear")
                    i += 3
                else:
                    i += 1