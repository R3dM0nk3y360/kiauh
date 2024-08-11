# ======================================================================= #
#  Copyright (C) 2020 - 2024 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
import json
from typing import List

from components.moonraker.moonraker import Moonraker
from components.octoeverywhere import (
    OE_DEPS_JSON_FILE,
    OE_DIR,
    OE_ENV_DIR,
    OE_INSTALL_SCRIPT,
    OE_INSTALLER_LOG_FILE,
    OE_REPO,
    OE_REQ_FILE,
    OE_SYS_CFG_NAME,
)
from components.octoeverywhere.octoeverywhere import Octoeverywhere
from core.instance_manager.instance_manager import InstanceManager
from utils.common import (
    check_install_dependencies,
    get_install_status,
    moonraker_exists,
)
from utils.config_utils import (
    remove_config_section,
)
from utils.fs_utils import run_remove_routines
from utils.git_utils import git_clone_wrapper
from utils.input_utils import get_confirm
from utils.logger import DialogType, Logger
from utils.sys_utils import (
    cmd_sysctl_manage,
    install_python_requirements,
    parse_packages_from_file,
)
from utils.types import ComponentStatus


def get_octoeverywhere_status() -> ComponentStatus:
    return get_install_status(OE_DIR, OE_ENV_DIR, Octoeverywhere)


def install_octoeverywhere() -> None:
    Logger.print_status("Installing OctoEverywhere for Klipper ...")

    # check if moonraker is installed. if not, notify the user and exit
    if not moonraker_exists():
        return

    force_clone = False
    oe_im = InstanceManager(Octoeverywhere)
    oe_instances: List[Octoeverywhere] = oe_im.instances
    if oe_instances:
        Logger.print_dialog(
            DialogType.INFO,
            [
                "OctoEverywhere is already installed!",
                "It is safe to run the installer again to link your "
                "printer or repair any issues.",
            ],
            padding_top=0,
            padding_bottom=0,
        )
        if not get_confirm("Re-run OctoEverywhere installation?"):
            Logger.print_info("Exiting OctoEverywhere for Klipper installation ...")
            return
        else:
            Logger.print_status("Re-Installing OctoEverywhere for Klipper ...")
            force_clone = True

    mr_im = InstanceManager(Moonraker)
    mr_instances: List[Moonraker] = mr_im.instances

    mr_names = [f"● {moonraker.data_dir_name}" for moonraker in mr_instances]
    if len(mr_names) > 1:
        Logger.print_dialog(
            DialogType.INFO,
            [
                "The following Moonraker instances were found:",
                *mr_names,
                "\n\n",
                "The setup will apply the same names to OctoEverywhere!",
            ],
            padding_top=0,
            padding_bottom=0,
        )

    if not get_confirm(
        "Continue OctoEverywhere for Klipper installation?",
        default_choice=True,
        allow_go_back=True,
    ):
        Logger.print_info("Exiting OctoEverywhere for Klipper installation ...")
        return

    try:
        git_clone_wrapper(OE_REPO, OE_DIR, force=force_clone)

        for moonraker in mr_instances:
            oe_im.current_instance = Octoeverywhere(suffix=moonraker.suffix)
            oe_im.create_instance()

        mr_im.restart_all_instance()

        Logger.print_dialog(
            DialogType.SUCCESS,
            ["OctoEverywhere for Klipper successfully installed!"],
            center_content=True,
        )

    except Exception as e:
        Logger.print_error(
            f"Error during OctoEverywhere for Klipper installation:\n{e}"
        )


def update_octoeverywhere() -> None:
    Logger.print_status("Updating OctoEverywhere for Klipper ...")
    try:
        Octoeverywhere.update()
        Logger.print_dialog(
            DialogType.SUCCESS,
            ["OctoEverywhere for Klipper successfully updated!"],
            center_content=True,
        )

    except Exception as e:
        Logger.print_error(f"Error during OctoEverywhere for Klipper update:\n{e}")


def remove_octoeverywhere() -> None:
    Logger.print_status("Removing OctoEverywhere for Klipper ...")
    mr_im = InstanceManager(Moonraker)
    mr_instances: List[Moonraker] = mr_im.instances
    ob_im = InstanceManager(Octoeverywhere)
    ob_instances: List[Octoeverywhere] = ob_im.instances

    try:
        remove_oe_instances(ob_im, ob_instances)
        remove_oe_dir()
        remove_oe_env()
        remove_config_section(f"include {OE_SYS_CFG_NAME}", mr_instances)
        run_remove_routines(OE_INSTALLER_LOG_FILE)
        Logger.print_dialog(
            DialogType.SUCCESS,
            ["OctoEverywhere for Klipper successfully removed!"],
            center_content=True,
        )

    except Exception as e:
        Logger.print_error(f"Error during OctoEverywhere for Klipper removal:\n{e}")


def install_oe_dependencies() -> None:
    oe_deps = []
    if OE_DEPS_JSON_FILE.exists():
        with open(OE_DEPS_JSON_FILE, "r") as deps:
            oe_deps = json.load(deps).get("debian", [])
    elif OE_INSTALL_SCRIPT.exists():
        oe_deps = parse_packages_from_file(OE_INSTALL_SCRIPT)

    if not oe_deps:
        raise ValueError("Error reading OctoEverywhere dependencies!")

    check_install_dependencies({*oe_deps})
    install_python_requirements(OE_ENV_DIR, OE_REQ_FILE)


def remove_oe_instances(
    instance_manager: InstanceManager,
    instance_list: List[Octoeverywhere],
) -> None:
    if not instance_list:
        Logger.print_info("No OctoEverywhere instances found. Skipped ...")
        return

    for instance in instance_list:
        Logger.print_status(f"Removing instance {instance.get_service_file_name()} ...")
        instance_manager.current_instance = instance
        instance_manager.stop_instance()
        instance_manager.disable_instance()
        instance_manager.delete_instance()

    cmd_sysctl_manage("daemon-reload")


def remove_oe_dir() -> None:
    Logger.print_status("Removing OctoEverywhere for Klipper directory ...")

    if not OE_DIR.exists():
        Logger.print_info(f"'{OE_DIR}' does not exist. Skipped ...")
        return

    run_remove_routines(OE_DIR)


def remove_oe_env() -> None:
    Logger.print_status("Removing OctoEverywhere for Klipper environment ...")

    if not OE_ENV_DIR.exists():
        Logger.print_info(f"'{OE_ENV_DIR}' does not exist. Skipped ...")
        return

    run_remove_routines(OE_ENV_DIR)
